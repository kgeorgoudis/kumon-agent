"""LangGraph orchestration entrypoints for tutor tasks."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph

import app.config as cfg
from app.agents.llm_client import get_llm_client
from app.agents.prompt_registry import get_prompt_version, load_prompt_bundle
from app.agents.state import TutorOutcome, TutorStepStatus, TutorTaskState, TutorTaskStatus, TutorTaskType
from app.agents.traces import list_task_traces, persist_step_finish, persist_step_start
from app.agents.tools import build_progress_fallback_suggestions
from app.domain.models import ProgressSuggestion
from app.persistence.database import Database, default_db

_ALLOWED_WORKSHEET_TYPES = {"drill", "mixed_review", "correction", "concept_reinforcement", "timed_fluency"}
_DIGIT_RE = re.compile(r"\d")
_ENGLISH_STOP_RE = re.compile(r"\b(the|is|and|for|of|that|with|are)\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_status(task: TutorTaskState, status: TutorTaskStatus) -> None:
    task.status = status
    task.updated_at = _now()


class ProgressGraphState(TypedDict, total=False):
    """Mutable state payload passed between graph nodes."""

    task: TutorTaskState
    deterministic_context: dict[str, Any]
    request_narrative: bool
    summary_el: str | None
    suggestions: list[dict[str, Any]]
    narrative_status: str
    validation_status: str
    error_code: str | None


_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)


def _extract_json_block(raw_text: str) -> dict[str, object]:
    # 1. Strip <think>…</think> blocks emitted by Qwen3 models
    candidate = _THINK_BLOCK_RE.sub("", raw_text).strip()
    # 2. Strip markdown code fences if present
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-z]*\n?", "", candidate).rstrip("`").strip()
    # 3. Find the outermost JSON object regardless of surrounding prose
    m = _JSON_OBJECT_RE.search(candidate)
    if m:
        candidate = m.group(0)
    return json.loads(candidate)


def _call_llm(task_type: TutorTaskType, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    persona, task_prompt = load_prompt_bundle(task_type)
    prompt = f"{persona}\n\n{task_prompt}"
    no_think_suffix = "" if cfg.LLM_THINKING_ENABLED else " /no_think"
    user_content = "Παράθεσε ΜΟΝΟ έγκυρο JSON με βάση τα ντετερμινιστικά δεδομένα:" + no_think_suffix + "\n" + json.dumps(payload, ensure_ascii=False)

    def _single_attempt() -> tuple[dict[str, Any] | None, str | None]:
        try:
            response = get_llm_client().chat.completions.create(
                model=cfg.LLM_MODEL,
                temperature=0.2,
                max_tokens=cfg.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception:
            return None, "ERR_LLM_UNAVAILABLE"

        content = ""
        finish_reason = None
        if response.choices:
            content = response.choices[0].message.content or ""
            finish_reason = getattr(response.choices[0], "finish_reason", None)
        if finish_reason == "length":
            return None, "ERR_LLM_TRUNCATED"
        try:
            return _extract_json_block(content), None
        except Exception:
            return None, "ERR_LLM_INVALID_JSON"

    result, error_code = _single_attempt()
    # Single automatic retry on invalid JSON (transient sampling failures)
    if result is None and error_code == "ERR_LLM_INVALID_JSON":
        result, error_code = _single_attempt()
    return result, error_code


def _normalize_suggestions(raw: list[object], known_skills: set[str]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rationale = str(item.get("rationale_el", "")).strip()
        if not rationale:
            continue
        target = item.get("target_micro_skill_id")
        target = str(target) if target is not None else None
        if target is not None and target not in known_skills:
            target = None
        worksheet_type = item.get("suggested_worksheet_type")
        worksheet_type = str(worksheet_type).strip().lower() if worksheet_type is not None else None
        if worksheet_type not in _ALLOWED_WORKSHEET_TYPES:
            worksheet_type = None
        suggestions.append(
            ProgressSuggestion(
                target_micro_skill_id=target,
                suggested_worksheet_type=worksheet_type,
                rationale_el=rationale,
                confidence=str(item.get("confidence")) if item.get("confidence") is not None else None,
            ).model_dump(mode="json")
        )
    return suggestions


def _build_progress_fallback(state: ProgressGraphState) -> None:
    context = state.get("deterministic_context", {})
    skill_rows = context.get("skill_progress") or context.get("skills", [])
    state["summary_el"] = "Η αφήγηση LLM δεν ήταν διαθέσιμη. Εμφανίζονται μόνο τα ντετερμινιστικά δεδομένα προόδου."
    state["narrative_status"] = "degraded"
    state["validation_status"] = "fallback"
    state["suggestions"] = build_progress_fallback_suggestions(skill_rows)


def _grounding_node(state: ProgressGraphState) -> ProgressGraphState:
    task = state["task"]
    _set_status(task, TutorTaskStatus.GROUNDING)
    return state


def _reasoning_node(state: ProgressGraphState) -> ProgressGraphState:
    task = state["task"]
    _set_status(task, TutorTaskStatus.REASONING)

    if not state.get("request_narrative", True):
        state["narrative_status"] = "not_requested"
        state["validation_status"] = "trusted"
        state["summary_el"] = None
        state["suggestions"] = []
        return state

    parsed, error_code = _call_llm(task.task_type, state.get("deterministic_context", {}))
    if parsed is None:
        state["error_code"] = error_code
        _build_progress_fallback(state)
        return state

    if task.task_type == TutorTaskType.PROGRESS_REPORT or task.task_type == TutorTaskType.NEXT_STEP_PLANNING:
        summary = str(parsed.get("summary_el", "")).strip() if task.task_type == TutorTaskType.PROGRESS_REPORT else None
        known_skills = {
            row["micro_skill_id"]
            for row in (state.get("deterministic_context", {}).get("skill_progress") or state.get("deterministic_context", {}).get("skills", []))
        }
        next_options = state.get("deterministic_context", {}).get("next_skill_options", {}).get("next_skills", [])
        for option in next_options:
            if isinstance(option, dict) and option.get("skill_id"):
                known_skills.add(str(option["skill_id"]))
        suggestions = _normalize_suggestions(parsed.get("suggestions", []), known_skills)
        state["summary_el"] = summary
        state["suggestions"] = suggestions
    elif task.task_type == TutorTaskType.WORKSHEET_REVIEW:
        state["summary_el"] = str(parsed.get("review_summary_el", "")).strip()
        state["suggestions"] = []
        state["deterministic_context"]["mistake_types"] = parsed.get("mistake_types", [])
        state["deterministic_context"]["next_step_suggestion_el"] = str(parsed.get("next_step_suggestion_el", "")).strip()

    state["narrative_status"] = "generated"
    state["validation_status"] = "trusted"
    return state


def _validation_node(state: ProgressGraphState) -> ProgressGraphState:
    task = state["task"]
    _set_status(task, TutorTaskStatus.VALIDATING)

    if state.get("narrative_status") == "generated" and task.task_type == TutorTaskType.PROGRESS_REPORT:
        summary = state.get("summary_el") or ""
        # Guard: empty or whitespace-only summary
        if not summary.strip():
            state["error_code"] = "ERR_LLM_EMPTY_SUMMARY"
            _build_progress_fallback(state)
            return state
        # Guard: raw digits in summary (conflicting facts)
        if _DIGIT_RE.search(summary):
            state["error_code"] = "ERR_LLM_CONFLICTING_FACTS"
            _build_progress_fallback(state)
            return state
        # Guard: English-language response
        if _ENGLISH_STOP_RE.search(summary):
            state["error_code"] = "ERR_LLM_WRONG_LANGUAGE"
            _build_progress_fallback(state)
            return state
        if not state.get("suggestions"):
            state["validation_status"] = "sanitized"
            _build_progress_fallback(state)
    elif state.get("narrative_status") == "generated" and task.task_type == TutorTaskType.WORKSHEET_REVIEW:
        if not state.get("summary_el"):
            state["error_code"] = "ERR_LLM_MISSING_SUMMARY"
            state["narrative_status"] = "degraded"
            state["validation_status"] = "fallback"
            state["summary_el"] = "Δεν ήταν διαθέσιμη η ανασκόπηση φύλλου. Εμφανίζονται μόνο τα ντετερμινιστικά δεδομένα."
    elif state.get("narrative_status") == "generated" and task.task_type == TutorTaskType.NEXT_STEP_PLANNING:
        if not state.get("suggestions"):
            state["error_code"] = "ERR_LLM_NO_SUGGESTIONS"
            state["narrative_status"] = "degraded"
            state["validation_status"] = "fallback"
            _build_progress_fallback(state)
    return state


def _build_progress_graph():
    graph = StateGraph(ProgressGraphState)  # type: ignore[arg-type]
    graph.add_node("grounding", _grounding_node)
    graph.add_node("reasoning", _reasoning_node)
    graph.add_node("validation", _validation_node)
    graph.set_entry_point("grounding")
    graph.add_edge("grounding", "reasoning")
    graph.add_edge("reasoning", "validation")
    graph.add_edge("validation", END)
    return graph.compile()


_PROGRESS_GRAPH = _build_progress_graph()


def create_task(task_type: TutorTaskType, *, child_id: str | None = None) -> TutorTaskState:
    now = _now()
    return TutorTaskState(
        task_type=task_type,
        child_id=child_id,
        prompt_version=get_prompt_version(task_type),
        created_at=now,
        updated_at=now,
    )


def create_progress_task(*, child_id: str | None = None) -> TutorTaskState:
    return create_task(TutorTaskType.PROGRESS_REPORT, child_id=child_id)


def _trace_summary(task_id: str, db: Database) -> dict[str, Any]:
    traces = list_task_traces(task_id, db=db)
    return {
        "step_count": len(traces),
        "step_names": [trace.step_name for trace in traces],
    }


def run_tutor_graph(
    initial_state: ProgressGraphState,
    *,
    db: Database = default_db,
) -> TutorOutcome:
    task = initial_state["task"]
    task.deterministic_context = dict(initial_state.get("deterministic_context", {}))
    db.save_agent_run(task)
    step_traces = []
    for step_name in ("grounding", "reasoning", "validation"):
        step_traces.append(
            persist_step_start(
            task.task_id,
            step_name,
            db=db,
            input_snapshot={"status": task.status.value},
            )
        )

    current_state: ProgressGraphState = _PROGRESS_GRAPH.invoke(dict(initial_state))

    for trace in step_traces:
        persist_step_finish(
            trace,
            status=TutorStepStatus.SUCCEEDED,
            db=db,
            output_snapshot={
                "status": current_state["task"].status.value,
                "narrative_status": current_state.get("narrative_status"),
            },
        )

    final_task = current_state["task"]
    if current_state.get("narrative_status") == "degraded":
        _set_status(final_task, TutorTaskStatus.COMPLETED)
    else:
        _set_status(final_task, TutorTaskStatus.COMPLETED)
    final_task.output = {
        "summary_el": current_state.get("summary_el"),
        "suggestions": current_state.get("suggestions", []),
        "narrative_status": current_state.get("narrative_status", "not_requested"),
        "validation_status": current_state.get("validation_status", "trusted"),
    }
    final_task.error_code = current_state.get("error_code")
    db.save_agent_run(final_task)
    return TutorOutcome(
        task_id=final_task.task_id,
        summary_el=current_state.get("summary_el"),
        suggestions=current_state.get("suggestions", []),
        deterministic_metrics=current_state.get("deterministic_context", {}),
        narrative_status=current_state.get("narrative_status", "not_requested"),
        validation_status=current_state.get("validation_status", "trusted"),
        error_code=current_state.get("error_code"),
        prompt_version=final_task.prompt_version,
        trace_summary=_trace_summary(final_task.task_id, db),
    )


def run_progress_graph(initial_state: ProgressGraphState, *, db: Database = default_db) -> ProgressGraphState:
    outcome = run_tutor_graph(initial_state, db=db)
    state = dict(initial_state)
    state["summary_el"] = outcome.summary_el
    state["suggestions"] = outcome.suggestions
    state["narrative_status"] = outcome.narrative_status
    state["validation_status"] = outcome.validation_status
    state["error_code"] = outcome.error_code
    state["task"] = db.get_agent_run(outcome.task_id) or state["task"]
    return state

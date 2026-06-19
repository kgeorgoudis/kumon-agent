"""Shared progress summary service for CLI and web entry points.

Deterministic metrics are always computed from local persistence.
LLM usage is optional and only enriches the report with Greek narrative text.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import app.config as cfg
from app.agents.llm_client import get_llm_client
from app.domain.knowledge_base import MICRO_SKILL_CATALOGUE
from app.domain.models import (
    ChildProfile,
    ProgressReport,
    ProgressSuggestion,
    ProgressWorksheetPoint,
    SkillProgress,
)
from app.persistence.database import Database, default_db

PROMPT_VERSION = "v1/progress_summary"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "v1" / "progress_summary.md"


def classify_accuracy_trend(values: list[float], delta_threshold: float = 3.0) -> str:
    """Classify trend from chronological accuracy values."""
    if len(values) < 2:
        return "insufficient_data"

    midpoint = max(1, len(values) // 2)
    prior = values[:midpoint]
    recent = values[midpoint:]
    if not recent:
        return "insufficient_data"

    delta = mean(recent) - mean(prior)
    if delta > delta_threshold:
        return "improving"
    if delta < -delta_threshold:
        return "declining"
    return "stable"


def load_progress_prompt() -> str:
    """Load the versioned prompt template for progress narrative generation."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def _find_next_possible_skills(practiced_skill_ids: set[str]) -> dict[str, object]:
    """Find skills the child could advance to based on mastery prerequisites.

    Returns a dict with keys: skill_id, name_el, description_el, prerequisites_met
    for up to 3 logical next skills.
    """
    practiced = set(practiced_skill_ids)
    candidates = []

    for skill_meta in MICRO_SKILL_CATALOGUE:
        skill_id = skill_meta.micro_skill_id.value

        # Skip if already practiced
        if skill_id in practiced:
            continue

        # Check if all prerequisites are met
        prereqs = getattr(skill_meta, 'prerequisites', [])
        if prereqs:
            if not all(p.value in practiced for p in prereqs):
                continue  # Not ready yet

        candidates.append({
            "skill_id": skill_id,
            "name_el": skill_meta.name_el,
            "description_el": skill_meta.description_el,
            "difficulty_level": skill_meta.difficulty_level,
            "prerequisites_met": True,
        })

    # Return the 3 easiest next skills (by difficulty level)
    sorted_candidates = sorted(candidates, key=lambda c: c["difficulty_level"])[:3]
    return {"next_skills": sorted_candidates}


def aggregate_skill_progress(points: list[ProgressWorksheetPoint]) -> list[SkillProgress]:
    """Aggregate chronological worksheet points into per-skill metrics."""
    bucket: dict[str, list[ProgressWorksheetPoint]] = defaultdict(list)
    for point in points:
        bucket[point.micro_skill_id].append(point)

    rows: list[SkillProgress] = []
    for micro_skill_id, skill_points in bucket.items():
        chronological = sorted(skill_points, key=lambda p: p.confirmed_at)
        accuracies = [p.accuracy_pct for p in chronological]
        rows.append(
            SkillProgress(
                micro_skill_id=micro_skill_id,
                worksheet_count=len(chronological),
                avg_accuracy_pct=mean(accuracies),
                last_accuracy_pct=accuracies[-1],
                trend=classify_accuracy_trend(accuracies),
            )
        )

    return sorted(rows, key=lambda row: (row.avg_accuracy_pct, row.micro_skill_id))


def build_progress_report(
    child: ChildProfile,
    limit: int = 20,
    include_narrative: bool = True,
    db: Database = default_db,
) -> ProgressReport:
    """Build deterministic progress report and optional LLM narrative."""
    points = db.list_progress_points(child_id=child.child_id, limit=limit)
    if not points:
        return ProgressReport(
            child_id=child.child_id,
            child_display_name=child.display_name,
            worksheet_count=0,
            overall_accuracy_pct=0.0,
            overall_trend="insufficient_data",
            summary_el="Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα για αναφορά προόδου.",
            narrative_status="not_requested" if not include_narrative else "degraded",
            llm_error_code=None if not include_narrative else "ERR_NO_DATA",
            prompt_version=PROMPT_VERSION,
        )

    chronological_points = sorted(points, key=lambda p: p.confirmed_at)
    overall_values = [p.accuracy_pct for p in chronological_points]
    report = ProgressReport(
        child_id=child.child_id,
        child_display_name=child.display_name,
        worksheet_count=len(chronological_points),
        date_from=chronological_points[0].confirmed_at,
        date_to=chronological_points[-1].confirmed_at,
        overall_accuracy_pct=mean(overall_values),
        overall_trend=classify_accuracy_trend(overall_values),
        skill_progress=aggregate_skill_progress(chronological_points),
        narrative_status="not_requested",
        prompt_version=PROMPT_VERSION,
    )

    if not include_narrative:
        return report

    narrative, suggestions, error_code = _generate_narrative(report, chronological_points)
    if narrative is not None:
        report.summary_el = narrative
        report.suggestions = suggestions
        report.narrative_status = "generated"
        report.llm_error_code = None
        return report

    report.narrative_status = "degraded"
    report.llm_error_code = error_code or "ERR_LLM_UNAVAILABLE"
    report.summary_el = (
        "Η αφήγηση LLM δεν ήταν διαθέσιμη. "
        "Εμφανίζονται μόνο τα ντετερμινιστικά δεδομένα προόδου."
    )
    report.suggestions = _deterministic_fallback_suggestions(report)
    return report


def _build_llm_payload(report: ProgressReport, points: list[ProgressWorksheetPoint]) -> dict[str, object]:
    """Build compact structured context sent to the LLM."""
    practiced_skills = {point.micro_skill_id for point in points}
    return {
        "child": {
            "child_id": report.child_id,
            "display_name": report.child_display_name,
        },
        "summary": {
            "worksheet_count": report.worksheet_count,
            "date_from": report.date_from.isoformat() if report.date_from else None,
            "date_to": report.date_to.isoformat() if report.date_to else None,
            "overall_accuracy_pct": round(report.overall_accuracy_pct, 2),
            "overall_trend": report.overall_trend,
        },
        "skills": [skill.model_dump(mode="json") for skill in report.skill_progress],
        "points": [
            {
                "instance_id": p.instance_id,
                "micro_skill_id": p.micro_skill_id,
                "accuracy_pct": p.accuracy_pct,
                "confirmed_at": p.confirmed_at.isoformat(),
            }
            for p in points
        ],
        "next_skill_options": _find_next_possible_skills(practiced_skills),
    }


def _extract_json_block(raw_text: str) -> dict[str, object]:
    """Parse LLM JSON output, accepting plain JSON or fenced JSON."""
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:]
    return json.loads(candidate.strip())


def _validate_suggestions(
    raw: list[object],
    practiced_skills: set[str],
    next_skill_options: list[dict[str, object]] | None = None,
) -> list[ProgressSuggestion]:
    """Validate and normalize suggestion payload from LLM response."""
    # Build set of known skills (practiced + next options)
    known_skills = practiced_skills.copy()
    if next_skill_options:
        for option in next_skill_options:
            if isinstance(option, dict):
                skill_id = option.get("skill_id")
                if skill_id:
                    known_skills.add(str(skill_id))

    suggestions: list[ProgressSuggestion] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rationale = str(item.get("rationale_el", "")).strip()
        if not rationale:
            continue
        target = item.get("target_micro_skill_id")
        if target is not None:
            target = str(target)
            if target not in known_skills:
                target = None
        suggestions.append(
            ProgressSuggestion(
                target_micro_skill_id=target,
                suggested_worksheet_type=(
                    str(item.get("suggested_worksheet_type"))
                    if item.get("suggested_worksheet_type") is not None
                    else None
                ),
                rationale_el=rationale,
                confidence=(
                    str(item.get("confidence"))
                    if item.get("confidence") is not None
                    else None
                ),
            )
        )
    return suggestions


def _generate_narrative(
    report: ProgressReport,
    points: list[ProgressWorksheetPoint],
) -> tuple[str | None, list[ProgressSuggestion], str | None]:
    """Ask local LLM for Greek summary and grounded suggestions."""
    payload = _build_llm_payload(report, points)
    prompt = load_progress_prompt()

    # Append /no_think when thinking is disabled so Qwen3-style models skip
    # chain-of-thought tokens and use the full max_tokens budget for JSON output.
    no_think_suffix = "" if cfg.LLM_THINKING_ENABLED else " /no_think"
    user_content = (
        "Παράθεσε ΜΟΝΟ έγκυρο JSON για αναφορά προόδου με βάση τα δεδομένα:"
        + no_think_suffix
        + "\n"
        + json.dumps(payload, ensure_ascii=False)
    )

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
        return None, [], "ERR_LLM_UNAVAILABLE"

    content = ""
    finish_reason = None
    if response.choices:
        content = response.choices[0].message.content or ""
        finish_reason = getattr(response.choices[0], "finish_reason", None)

    if finish_reason == "length":
        # Model hit max_tokens before completing JSON.  Raise KUMON_LLM_MAX_TOKENS.
        return None, [], "ERR_LLM_TRUNCATED"

    try:
        parsed = _extract_json_block(content)
    except Exception:
        return None, [], "ERR_LLM_INVALID_JSON"

    summary = str(parsed.get("summary_el", "")).strip()
    if not summary:
        return None, [], "ERR_LLM_MISSING_SUMMARY"

    raw_suggestions = parsed.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        raw_suggestions = []
    practiced = {point.micro_skill_id for point in points}
    next_options = payload.get("next_skill_options", {}).get("next_skills", [])
    suggestions = _validate_suggestions(raw_suggestions, practiced, next_options)
    if not suggestions:
        suggestions = _deterministic_fallback_suggestions(report)

    return summary, suggestions, None


def _deterministic_fallback_suggestions(report: ProgressReport) -> list[ProgressSuggestion]:
    """Produce safe fallback suggestions when LLM text is unavailable."""
    if not report.skill_progress:
        return []

    # Find the weakest skill (lowest average accuracy)
    weakest = min(report.skill_progress, key=lambda row: row.avg_accuracy_pct)

    # Determine the type of suggestion based on performance
    if weakest.avg_accuracy_pct >= 90:
        # Child is ready to advance
        worksheet_type = "mixed_review"
        rationale = (
            f"Η '{weakest.micro_skill_id}' έχει εξασκηθεί καλά. "
            "Δοκιμάστε ένα μικτό φύλλο για να διατηρηθούν αυτές οι δεξιότητες σε χρήση."
        )
    elif weakest.avg_accuracy_pct >= 70:
        # Still practicing, needs more work
        worksheet_type = "drill"
        rationale = (
            f"Η '{weakest.micro_skill_id}' χρειάζεται περισσότερη εξάσκηση. "
            "Ένα κανονικό φύλλο θα βοηθήσει στην κατακτησή της."
        )
    else:
        # Struggling, may need scaffolding
        worksheet_type = "correction"
        rationale = (
            f"Η '{weakest.micro_skill_id}' φαίνεται δύσκολη. "
            "Ένα φύλλο με πιο εύκολες ασκήσεις θα βοηθήσει να κερδίσει αυτοπεποίθηση."
        )

    return [
        ProgressSuggestion(
            target_micro_skill_id=weakest.micro_skill_id,
            suggested_worksheet_type=worksheet_type,
            rationale_el=rationale,
            confidence="medium",
        )
    ]


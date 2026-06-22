"""Shared progress summary service for CLI and web entry points.

Deterministic metrics are always computed from local persistence.
LLM usage is optional and only enriches the report with Greek narrative text.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from app.agents.agent_graph import create_progress_task, run_tutor_graph
from app.agents.prompt_registry import load_prompt_bundle
from app.domain.knowledge_base import MICRO_SKILL_CATALOGUE
from app.domain.models import (
    ChildProfile,
    ProgressReport,
    ProgressSuggestion,
    ProgressWorksheetPoint,
    SkillProgress,
)
from app.persistence.database import Database, default_db

PROMPT_VERSION = "v1/kumon_tutor_progress_summary"


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
    """Load persona + task prompt for progress narrative generation."""
    persona, task_prompt = load_prompt_bundle(create_progress_task().task_type)
    return f"{persona}\n\n{task_prompt}"


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

    task = create_progress_task(child_id=child.child_id)
    outcome = run_tutor_graph(
        {
            "task": task,
            "deterministic_context": _build_llm_payload(report, chronological_points),
            "request_narrative": True,
        },
        db=db,
    )
    report.task_id = outcome.task_id
    report.trace_summary = outcome.trace_summary
    report.prompt_version = outcome.prompt_version or PROMPT_VERSION
    report.summary_el = outcome.summary_el
    report.suggestions = [ProgressSuggestion.model_validate(item) for item in outcome.suggestions]
    report.narrative_status = outcome.narrative_status
    report.llm_error_code = outcome.error_code
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



"""Deterministic tool wrappers used by LangGraph nodes."""

from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean

from app.domain.models import ChildProfile, ProgressReport
from app.domain.models import MicroSkillId, ProgressSuggestion
from app.domain.knowledge_base import KumonKnowledgeBase
from app.domain.models import ProgressWorksheetPoint, SkillProgress
from app.persistence.database import Database, default_db
from app.services.progression_service import evaluate_progression


def _classify_accuracy_trend(values: list[float], delta_threshold: float = 3.0) -> str:
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


def _aggregate_skill_progress(points: list[ProgressWorksheetPoint]) -> list[SkillProgress]:
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
                trend=_classify_accuracy_trend(accuracies),
            )
        )
    return sorted(rows, key=lambda row: (row.avg_accuracy_pct, row.micro_skill_id))


def build_progress_deterministic_context(
    *,
    child: ChildProfile,
    limit: int,
    db: Database = default_db,
) -> dict[str, object]:
    """Collect deterministic progress context without invoking any model."""
    points = db.list_progress_points(child_id=child.child_id, limit=limit)
    chronological = sorted(points, key=lambda p: p.confirmed_at)
    accuracies = [p.accuracy_pct for p in chronological]
    overall = sum(accuracies) / len(accuracies) if accuracies else 0.0
    return {
        "child": {
            "child_id": child.child_id,
            "display_name": child.display_name,
        },
        "worksheet_count": len(chronological),
        "overall_accuracy_pct": overall,
        "overall_trend": _classify_accuracy_trend(accuracies) if accuracies else "insufficient_data",
        "skill_progress": [s.model_dump(mode="json") for s in _aggregate_skill_progress(chronological)],
        "points": [p.model_dump(mode="json") for p in chronological],
    }


def build_progress_fallback_outcome(report: ProgressReport) -> tuple[str, list[dict[str, object]]]:
    """Return deterministic fallback summary and suggestion payloads."""
    summary = (
        "Η αφήγηση LLM δεν ήταν διαθέσιμη. "
        "Εμφανίζονται μόνο τα ντετερμινιστικά δεδομένα προόδου."
    )
    suggestions = [s.model_dump(mode="json") for s in report.suggestions]
    return summary, suggestions


def build_progress_fallback_suggestions(skill_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build deterministic fallback suggestions from serialized skill rows."""
    if not skill_rows:
        return []
    weakest = min(skill_rows, key=lambda row: float(row.get("avg_accuracy_pct", 0.0)))
    avg = float(weakest.get("avg_accuracy_pct", 0.0))
    worksheet_type = "mixed_review" if avg >= 90 else "drill" if avg >= 70 else "correction"
    return [
        ProgressSuggestion(
            target_micro_skill_id=str(weakest.get("micro_skill_id")),
            suggested_worksheet_type=worksheet_type,
            rationale_el=f"Η '{weakest.get('micro_skill_id')}' χρειάζεται το επόμενο μικρό βήμα εξάσκησης.",
            confidence="medium",
        ).model_dump(mode="json")
    ]


def build_progression_context(
    *,
    child_id: str,
    micro_skill_id: str,
    db: Database = default_db,
) -> dict[str, object]:
    """Collect deterministic progression decision context for planning tasks."""
    decision = evaluate_progression(
        child_id=child_id,
        micro_skill_id=MicroSkillId(micro_skill_id),
        db=db,
        persist=False,
    )
    return decision.model_dump(mode="json")


def build_manual_review_context(
    *,
    instance_id: str,
    db: Database = default_db,
) -> dict[str, object]:
    """Return deterministic worksheet + score snapshot context for review tasks."""
    worksheet = db.get_worksheet_instance(instance_id)
    submission = db.get_confirmed_manual_submission_for_instance(instance_id)
    if worksheet is None:
        return {"error": "ERR_WORKSHEET_NOT_FOUND", "instance_id": instance_id}
    if submission is None:
        return {"error": "ERR_SUBMISSION_NOT_FOUND", "instance_id": instance_id}

    snapshot = db.get_latest_score_snapshot_for_submission(submission.submission_id)
    details = json.loads(snapshot.details_json) if snapshot else {}
    entry_details = details.get("entries", []) if isinstance(details, dict) else []
    entries = [e.model_dump(mode="json") for e in db.get_manual_answer_entries(submission.submission_id)]
    merged_entries = []
    for idx, exercise in enumerate(worksheet.exercises):
        stored = entries[idx] if idx < len(entries) else {}
        detail = entry_details[idx] if idx < len(entry_details) and isinstance(entry_details[idx], dict) else {}
        merged_entries.append(
            {
                "slot_index": idx,
                "exercise_id": exercise.exercise_id,
                "problem_text": exercise.problem_text,
                "child_answer": stored.get("normalized_value", ""),
                "raw_value": stored.get("raw_value", ""),
                "correct_answer": detail.get(
                    "correct_answer",
                    exercise.canonical_answer or str(exercise.answer or ""),
                ),
                "is_valid": stored.get("is_valid", False),
                "is_correct": stored.get("normalized_value", "")
                == detail.get("correct_answer", exercise.canonical_answer or str(exercise.answer or "")),
            }
        )
    skill_meta = KumonKnowledgeBase.get_micro_skill(worksheet.micro_skill_id)
    return {
        "instance_id": instance_id,
        "submission_id": submission.submission_id,
        "micro_skill_id": worksheet.micro_skill_id.value,
        "micro_skill_name_el": skill_meta.name_el if skill_meta else worksheet.title_el,
        "title_el": worksheet.title_el,
        "exercise_count": len(worksheet.exercises),
        "accuracy_pct": snapshot.accuracy_pct if snapshot else None,
        "entries": merged_entries,
    }


def build_next_step_plan_context(
    *,
    child: ChildProfile,
    limit: int,
    db: Database = default_db,
) -> dict[str, object]:
    """Collect deterministic context for next-step planning tasks."""
    progress = build_progress_deterministic_context(child=child, limit=limit, db=db)
    weakest_skill_id = None
    skill_rows = progress.get("skill_progress", [])
    if skill_rows:
        weakest_skill_id = min(skill_rows, key=lambda row: row["avg_accuracy_pct"])["micro_skill_id"]
    progression = (
        build_progression_context(child_id=child.child_id, micro_skill_id=weakest_skill_id, db=db)
        if weakest_skill_id
        else None
    )
    progress["progression_decision"] = progression
    return progress




from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.domain.models import TutorStepStatus, TutorStepTrace, TutorTaskState, TutorTaskStatus, TutorTaskType
from app.observability.service import TraceService
from app.persistence.database import Database


def test_degraded_run_persists_error_code_and_fallback_metadata(tmp_path: Path) -> None:
    db = Database(db_path=tmp_path / "observability-integration.db")
    service = TraceService(db=db)

    run = TutorTaskState(
        task_id="task-integration",
        task_type=TutorTaskType.WORKSHEET_REVIEW,
        prompt_version="v1/worksheet_review",
        status=TutorTaskStatus.DEGRADED,
        error_code="LLM_TIMEOUT",
        deterministic_context={"skill_id": "subtraction_single_digit"},
        output={"fallback_used": True, "validation_status": "fallback"},
    )
    db.save_agent_run(run)

    step = TutorStepTrace(
        task_id=run.task_id,
        step_name="invoke_llm",
        status=TutorStepStatus.FAILED,
        input_snapshot={"phase": "llm"},
        output_snapshot={"fallback_used": True},
        error_code="LLM_TIMEOUT",
    )
    db.save_agent_step_run(step)

    details = service.get_run_details(run.task_id, include_full=True)

    assert details is not None
    assert details["status"] == TutorTaskStatus.DEGRADED.value
    assert details["error_code"] == "LLM_TIMEOUT"
    assert details["output_summary"]["fallback_used"] is True
    assert details["steps"][0]["error_code"] == "LLM_TIMEOUT"


def test_successful_run_persists_all_steps_and_status(tmp_path: Path) -> None:
    """T011 – Successful tutor run stores status, steps, and sanitized output."""
    db = Database(db_path=tmp_path / "observability-success.db")
    service = TraceService(db=db)

    base_ts = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)

    run = TutorTaskState(
        task_id="task-success",
        task_type=TutorTaskType.PROGRESS_REPORT,
        prompt_version="v1/progress_summary",
        status=TutorTaskStatus.COMPLETED,
        deterministic_context={
            "skill_id": "multiplication_2_5",
            "worksheet_count": 5,
            "avg_accuracy_pct": 82.5,
        },
        output={
            "summary_el": "Εξαιρετική πρόοδος!",
            "recommendations_count": 2,
            "narrative_status": "generated",
        },
    )
    db.save_agent_run(run)

    steps = [
        ("ground_context", TutorStepStatus.SUCCEEDED, None),
        ("invoke_llm", TutorStepStatus.SUCCEEDED, None),
        ("validate_output", TutorStepStatus.SUCCEEDED, None),
    ]
    for i, (name, status, error_code) in enumerate(steps):
        db.save_agent_step_run(
            TutorStepTrace(
                step_id=f"step-success-{i}",
                task_id=run.task_id,
                step_name=name,
                status=status,
                input_snapshot={"phase": name},
                output_snapshot={"ok": True},
                error_code=error_code,
                started_at=base_ts + timedelta(seconds=i * 2),
                finished_at=base_ts + timedelta(seconds=i * 2 + 1),
            )
        )

    details = service.get_run_details(run.task_id, include_full=True)

    assert details is not None
    assert details["status"] == TutorTaskStatus.COMPLETED.value
    assert details["error_code"] is None
    assert len(details["steps"]) == 3
    assert [s["step_name"] for s in details["steps"]] == [
        "ground_context",
        "invoke_llm",
        "validate_output",
    ]
    # Constitution XII: sanitized output must not expose full narrative text
    # but aggregate metrics should be present
    assert details["output_summary"]["recommendations_count"] == 2
    assert details["output_summary"]["narrative_status"] == "generated"
    # output_summary truncates long strings but keeps short ones
    assert details["output_summary"]["summary_el"] is not None



from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import app.cli.main as cli_main
from app.domain.models import (
    TutorStepStatus,
    TutorStepTrace,
    TutorTaskState,
    TutorTaskStatus,
    TutorTaskType,
)
from app.observability.service import TraceService
from app.persistence.database import Database


def test_list_runs_filters_by_status_and_task_type(tmp_path: Path) -> None:
    db = Database(db_path=tmp_path / "observability.db")
    service = TraceService(db=db)

    completed_run = TutorTaskState(
        task_id="task-completed",
        task_type=TutorTaskType.PROGRESS_REPORT,
        prompt_version="v1/progress_summary",
        status=TutorTaskStatus.COMPLETED,
        deterministic_context={"skill_id": "addition_single_digit"},
        output={"summary_el": "done"},
    )
    degraded_run = TutorTaskState(
        task_id="task-degraded",
        task_type=TutorTaskType.WORKSHEET_REVIEW,
        prompt_version="v1/worksheet_review",
        status=TutorTaskStatus.DEGRADED,
        error_code="LLM_TIMEOUT",
        deterministic_context={"skill_id": "subtraction_single_digit"},
        output={"fallback_used": True},
    )
    db.save_agent_run(completed_run)
    db.save_agent_run(degraded_run)

    results = service.list_runs(
        status=TutorTaskStatus.DEGRADED,
        task_type=TutorTaskType.WORKSHEET_REVIEW,
        limit=10,
    )

    assert len(results) == 1
    assert results[0]["task_id"] == degraded_run.task_id
    assert results[0]["error_code"] == "LLM_TIMEOUT"


def test_list_runs_accepts_string_filters(tmp_path: Path) -> None:
    db = Database(db_path=tmp_path / "observability-strings.db")
    service = TraceService(db=db)

    run = TutorTaskState(
        task_id="task-string-filters",
        task_type=TutorTaskType.WORKSHEET_REVIEW,
        prompt_version="v1/worksheet_review",
        status=TutorTaskStatus.DEGRADED,
        error_code="LLM_TIMEOUT",
        deterministic_context={"skill_id": "subtraction_single_digit"},
        output={"fallback_used": True},
    )
    db.save_agent_run(run)

    results = service.list_runs(status="degraded", task_type="worksheet_review", limit=10)

    assert len(results) == 1
    assert results[0]["task_id"] == run.task_id


def test_get_run_details_sanitizes_pii_and_returns_steps(tmp_path: Path) -> None:
    db = Database(db_path=tmp_path / "observability-details.db")
    service = TraceService(db=db)

    run = TutorTaskState(
        task_id="task-details",
        task_type=TutorTaskType.PROGRESS_REPORT,
        prompt_version="v1/progress_summary",
        status=TutorTaskStatus.COMPLETED,
        deterministic_context={"child_name": "Ελένη", "skill_id": "addition_single_digit"},
        output={"summary_el": "ok", "recommendations_count": 2},
    )
    db.save_agent_run(run)

    step = TutorStepTrace(
        task_id=run.task_id,
        step_name="reasoning",
        status=TutorStepStatus.SUCCEEDED,
        input_snapshot={"child_name": "Ελένη", "phase": "reasoning"},
        output_snapshot={"summary": "ok"},
    )
    db.save_agent_step_run(step)

    details = service.get_run_details(run.task_id, include_full=True)

    assert details is not None
    assert details["task_id"] == run.task_id
    assert details["deterministic_context"]["skill_id"] == "addition_single_digit"
    assert "child_name" not in details["deterministic_context"]
    assert details["steps"][0]["step_name"] == "reasoning"
    assert "child_name" not in details["steps"][0]["input_snapshot"]


def test_cli_traces_show_and_list_work_with_string_filters(tmp_path: Path, monkeypatch) -> None:
    db = Database(db_path=tmp_path / "observability-cli.db")
    monkeypatch.setattr(cli_main, "default_db", db)
    monkeypatch.setattr(cli_main, "trace_service", TraceService(db=db))

    run = TutorTaskState(
        task_id="task-cli",
        task_type=TutorTaskType.PROGRESS_REPORT,
        prompt_version="v1/progress_summary",
        status=TutorTaskStatus.COMPLETED,
        deterministic_context={"skill_id": "addition_single_digit"},
        output={"summary_el": "done"},
    )
    db.save_agent_run(run)

    runner = CliRunner()

    list_result = runner.invoke(cli_main.app, ["traces", "list", "--status", "completed", "--type", "progress_report", "--json"])
    assert list_result.exit_code == 0, list_result.output
    payload = list_result.stdout
    assert "task-cli" in payload

    show_result = runner.invoke(cli_main.app, ["traces", "show", "task-cli", "--json"])
    assert show_result.exit_code == 0, show_result.output
    assert "task-cli" in show_result.stdout


# ── T010: Degraded-state diagnostics & fallback metadata ──────────────────────


def test_list_runs_returns_degraded_runs_with_error_code(tmp_path: Path) -> None:
    """T010 – Degraded runs are listable and expose their error codes."""
    db = Database(db_path=tmp_path / "t010.db")
    service = TraceService(db=db)

    for i, (task_type, status, error_code) in enumerate(
        [
            (TutorTaskType.PROGRESS_REPORT, TutorTaskStatus.COMPLETED, None),
            (TutorTaskType.WORKSHEET_REVIEW, TutorTaskStatus.DEGRADED, "LLM_TIMEOUT"),
            (TutorTaskType.NEXT_STEP_PLANNING, TutorTaskStatus.FAILED, "TOOL_ERROR"),
        ]
    ):
        db.save_agent_run(
            TutorTaskState(
                task_id=f"t010-{i}",
                task_type=task_type,
                prompt_version="v1/test",
                status=status,
                error_code=error_code,
                deterministic_context={"skill_id": "addition_single_digit"},
                output={},
            )
        )

    degraded = service.list_runs(status=TutorTaskStatus.DEGRADED)
    assert len(degraded) == 1
    assert degraded[0]["error_code"] == "LLM_TIMEOUT"

    failed = service.list_runs(status=TutorTaskStatus.FAILED)
    assert len(failed) == 1
    assert failed[0]["error_code"] == "TOOL_ERROR"

    all_runs = service.list_runs()
    assert len(all_runs) == 3


def test_list_runs_fallback_metadata_visible_in_get_run_details(tmp_path: Path) -> None:
    """T010 – Fallback metadata stored in output is accessible via get_run_details."""
    db = Database(db_path=tmp_path / "t010-fallback.db")
    service = TraceService(db=db)

    run = TutorTaskState(
        task_id="task-fallback",
        task_type=TutorTaskType.WORKSHEET_REVIEW,
        prompt_version="v1/worksheet_review",
        status=TutorTaskStatus.DEGRADED,
        error_code="LLM_UNAVAILABLE",
        deterministic_context={"skill_id": "multiplication_2_5"},
        output={
            "fallback_used": True,
            "fallback_reason": "LLM server offline",
            "validation_status": "fallback",
            "narrative_status": "degraded",
        },
    )
    db.save_agent_run(run)

    details = service.get_run_details(run.task_id, include_full=False)

    assert details is not None
    assert details["status"] == TutorTaskStatus.DEGRADED.value
    assert details["error_code"] == "LLM_UNAVAILABLE"
    assert details["output_summary"]["fallback_used"] is True
    assert details["output_summary"]["fallback_reason"] == "LLM server offline"


# ── T016: Audit-oriented – linked run/step retrieval & stable ordering ─────────


def test_run_step_linkage_stable_chronological_ordering(tmp_path: Path) -> None:
    """T016 – Steps are linked to their run and returned in start-time order."""
    db = Database(db_path=tmp_path / "t016.db")
    service = TraceService(db=db)

    run = TutorTaskState(
        task_id="task-audit",
        task_type=TutorTaskType.PROGRESS_REPORT,
        prompt_version="v1/progress_summary",
        status=TutorTaskStatus.COMPLETED,
        deterministic_context={"skill_id": "multiplication_2_5"},
        output={"summary_el": "ok"},
    )
    db.save_agent_run(run)

    step_names = ["ground_context", "invoke_llm", "validate_output"]
    base_ts = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta

    for i, name in enumerate(step_names):
        db.save_agent_step_run(
            TutorStepTrace(
                step_id=f"step-{i}",
                task_id=run.task_id,
                step_name=name,
                status=TutorStepStatus.SUCCEEDED,
                input_snapshot={"phase": name},
                output_snapshot={"ok": True},
                started_at=base_ts + timedelta(seconds=i * 2),
                finished_at=base_ts + timedelta(seconds=i * 2 + 1),
            )
        )

    details = service.get_run_details(run.task_id, include_full=True)

    assert details is not None
    assert details["task_id"] == run.task_id
    returned_names = [s["step_name"] for s in details["steps"]]
    assert returned_names == step_names, "Steps must be returned in chronological order"


def test_multiple_runs_ordered_newest_first(tmp_path: Path) -> None:
    """T016 – list_runs returns newest runs first for audit-style review."""
    db = Database(db_path=tmp_path / "t016-ordering.db")
    service = TraceService(db=db)

    from datetime import timedelta

    base_ts = datetime(2026, 6, 27, 8, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        run = TutorTaskState(
            task_id=f"task-order-{i}",
            task_type=TutorTaskType.PROGRESS_REPORT,
            prompt_version="v1/progress_summary",
            status=TutorTaskStatus.COMPLETED,
            deterministic_context={},
            output={},
            created_at=base_ts + timedelta(minutes=i),
            updated_at=base_ts + timedelta(minutes=i),
        )
        db.save_agent_run(run)

    runs = service.list_runs()
    created_ats = [r["created_at"] for r in runs]
    assert created_ats == sorted(created_ats, reverse=True), "Runs must be newest-first"


# ── T018: Non-blocking graceful degradation when storage unavailable ───────────


def test_list_runs_returns_empty_list_when_db_raises(tmp_path: Path) -> None:
    """T018 – TraceService.list_runs never raises; returns [] on storage error."""
    mock_db = MagicMock()
    mock_db.list_agent_runs.side_effect = Exception("DB unavailable")
    service = TraceService(db=mock_db)

    result = service.list_runs()
    assert result == []


def test_get_run_details_returns_none_when_db_raises(tmp_path: Path) -> None:
    """T018 – TraceService.get_run_details never raises; returns None on storage error."""
    mock_db = MagicMock()
    mock_db.get_agent_run.side_effect = Exception("DB unavailable")
    service = TraceService(db=mock_db)

    result = service.get_run_details("any-id")
    assert result is None


def test_list_runs_returns_empty_list_when_invalid_filter_given(tmp_path: Path) -> None:
    """T018 – TraceService.list_runs returns [] when an invalid status string is given."""
    db = Database(db_path=tmp_path / "t018-invalid.db")
    service = TraceService(db=db)

    result = service.list_runs(status="NOT_A_VALID_STATUS")
    assert result == []


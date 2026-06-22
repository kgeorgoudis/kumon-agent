"""In-memory trace helpers for LangGraph step execution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.state import TutorStepStatus, TutorStepTrace
from app.persistence.database import Database, default_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_step_trace(
    task_id: str,
    step_name: str,
    *,
    status: TutorStepStatus = TutorStepStatus.RUNNING,
    input_snapshot: dict[str, Any] | None = None,
) -> TutorStepTrace:
    """Create a new in-memory trace record for a graph step."""
    return TutorStepTrace(
        step_id=str(uuid.uuid4()),
        task_id=task_id,
        step_name=step_name,
        status=status,
        input_snapshot=input_snapshot or {},
        started_at=_now(),
    )


def finalize_step_trace(
    trace: TutorStepTrace,
    *,
    status: TutorStepStatus,
    output_snapshot: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> TutorStepTrace:
    """Mark a running step trace as finished with output metadata."""
    trace.status = status
    trace.finished_at = _now()
    trace.output_snapshot = output_snapshot or {}
    trace.error_code = error_code
    return trace


def persist_step_start(
    task_id: str,
    step_name: str,
    *,
    db: Database = default_db,
    input_snapshot: dict[str, Any] | None = None,
) -> TutorStepTrace:
    """Create and persist a running step trace."""
    trace = new_step_trace(task_id, step_name, input_snapshot=input_snapshot)
    db.save_agent_step_run(trace)
    return trace


def persist_step_finish(
    trace: TutorStepTrace,
    *,
    status: TutorStepStatus,
    db: Database = default_db,
    output_snapshot: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> TutorStepTrace:
    """Finalize and persist a previously started step trace."""
    finalized = finalize_step_trace(
        trace,
        status=status,
        output_snapshot=output_snapshot,
        error_code=error_code,
    )
    db.save_agent_step_run(finalized)
    return finalized


def list_task_traces(task_id: str, *, db: Database = default_db) -> list[TutorStepTrace]:
    """Load persisted step traces for one task."""
    return db.list_agent_step_runs(task_id)



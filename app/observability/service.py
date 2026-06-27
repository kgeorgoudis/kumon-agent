from __future__ import annotations

from typing import Any

from app.domain.models import TutorStepTrace, TutorTaskState, TutorTaskStatus, TutorTaskType
from app.persistence.database import Database


class TraceService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    def list_runs(
        self,
        *,
        status: TutorTaskStatus | str | None = None,
        task_type: TutorTaskType | str | None = None,
        hours: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        try:
            return self.db.list_agent_runs(
                status=self._coerce_task_status(status),
                task_type=self._coerce_task_type(task_type),
                hours=hours,
                limit=limit,
                offset=offset,
            )
        except Exception:
            return []

    def get_run_details(self, task_id: str, *, include_full: bool = False) -> dict[str, Any] | None:
        try:
            run = self.db.get_agent_run(task_id)
        except Exception:
            return None
        if run is None:
            return None

        steps = [self._serialize_step(step, include_full=include_full) for step in self.db.list_agent_step_runs(task_id)]
        return {
            "task_id": run.task_id,
            "task_type": run.task_type.value,
            "status": run.status.value,
            "prompt_version": run.prompt_version,
            "error_code": run.error_code,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
            "deterministic_context": self._sanitize_context(run.deterministic_context),
            "output_summary": self._sanitize_output(run.output),
            "steps": steps,
        }

    def _serialize_step(self, step: TutorStepTrace, *, include_full: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "step_id": step.step_id,
            "step_name": step.step_name,
            "status": step.status.value,
            "started_at": step.started_at.isoformat(),
            "finished_at": step.finished_at.isoformat() if step.finished_at else None,
            "error_code": step.error_code,
            "input_snapshot": self._sanitize_context(step.input_snapshot) if include_full else {},
            "output_snapshot": self._sanitize_output(step.output_snapshot) if include_full else {},
        }
        if not include_full:
            payload.pop("input_snapshot", None)
            payload.pop("output_snapshot", None)
        return payload

    def _sanitize_context(self, data: dict[str, Any] | None) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in (data or {}).items():
            if key in {"child_name", "display_name", "name", "email", "phone", "address", "api_key", "token", "password", "secret", "authorization"}:
                continue
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_context(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_output(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {}
        sanitized = self._sanitize_context(data)
        if "summary_el" in sanitized and isinstance(sanitized["summary_el"], str):
            sanitized["summary_el"] = sanitized["summary_el"][:200]
        return sanitized

    def _coerce_task_status(self, value: TutorTaskStatus | str | None) -> TutorTaskStatus | None:
        if value is None or isinstance(value, TutorTaskStatus):
            return value
        if isinstance(value, str):
            return TutorTaskStatus(value)
        raise TypeError(f"Unsupported task status: {value!r}")

    def _coerce_task_type(self, value: TutorTaskType | str | None) -> TutorTaskType | None:
        if value is None or isinstance(value, TutorTaskType):
            return value
        if isinstance(value, str):
            return TutorTaskType(value)
        raise TypeError(f"Unsupported task type: {value!r}")

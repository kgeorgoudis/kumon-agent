from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.agents.traces import list_task_traces, persist_step_finish, persist_step_start
from app.agents.state import TutorStepStatus
from app.persistence.database import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "agent_traces.db")


def test_persist_step_lifecycle(db: Database):
    task_id = "task-1"

    start = persist_step_start(
        task_id,
        "grounding",
        db=db,
        input_snapshot={"phase": "start"},
    )

    finished = persist_step_finish(
        start,
        status=TutorStepStatus.SUCCEEDED,
        db=db,
        output_snapshot={"phase": "done"},
    )

    rows = list_task_traces(task_id, db=db)
    assert len(rows) == 1
    assert rows[0].step_id == finished.step_id
    assert rows[0].status == TutorStepStatus.SUCCEEDED
    assert rows[0].input_snapshot == {"phase": "start"}
    assert rows[0].output_snapshot == {"phase": "done"}


def test_persist_multiple_steps_ordered_by_start_time(db: Database):
    task_id = "task-2"
    step_a = persist_step_start(task_id, "grounding", db=db)
    step_b = persist_step_start(task_id, "reasoning", db=db)
    persist_step_finish(step_a, status=TutorStepStatus.SUCCEEDED, db=db)
    persist_step_finish(step_b, status=TutorStepStatus.SUCCEEDED, db=db)

    rows = list_task_traces(task_id, db=db)
    assert [r.step_name for r in rows] == ["grounding", "reasoning"]


def test_agent_run_can_be_reloaded_with_prompt_version(db: Database):
    from app.agents.agent_graph import create_progress_task, run_tutor_graph

    task = create_progress_task(child_id="trace-child")
    outcome = run_tutor_graph(
        {
            "task": task,
            "deterministic_context": {"skills": []},
            "request_narrative": False,
        },
        db=db,
    )

    loaded = db.get_agent_run(outcome.task_id)
    assert loaded is not None
    assert loaded.prompt_version == f"{cfg.PROMPT_VERSION}/progress_summary"



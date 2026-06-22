from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.agent_graph import ProgressGraphState, create_progress_task, run_progress_graph
from app.agents.state import TutorTaskStatus
from app.persistence.database import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "agent_state.db")


def test_create_progress_task_defaults_prompt_version():
    task = create_progress_task(child_id="child-123")
    assert task.task_type.value == "progress_report"
    assert task.prompt_version == "v1/progress_summary"
    assert task.child_id == "child-123"


def test_run_progress_graph_completes_and_persists_traces(db: Database):
    task = create_progress_task(child_id="child-xyz")
    state: ProgressGraphState = {"task": task}

    result = run_progress_graph(state, db=db)

    out_task = result["task"]
    assert out_task.status == TutorTaskStatus.COMPLETED

    persisted = db.get_agent_run(task.task_id)
    assert persisted is not None
    assert persisted.status == TutorTaskStatus.COMPLETED

    steps = db.list_agent_step_runs(task.task_id)
    assert [s.step_name for s in steps] == ["grounding", "reasoning", "validation"]
    assert all(s.status.value == "succeeded" for s in steps)



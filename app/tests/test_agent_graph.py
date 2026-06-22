from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.agents.agent_graph import create_progress_task, create_task, run_tutor_graph
from app.agents.state import TutorTaskType
from app.agents.tools import build_manual_review_context, build_next_step_plan_context
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.submission_service import confirm_and_score, set_answers_on_draft, start_submission
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "agent_graph.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def child(db: Database) -> ChildProfile:
    profile = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(profile)
    return profile


def _seed_progress(db: Database, child: ChildProfile, seed: int, wrong_first: bool = False) -> str:
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)
    answers = [str(ex.answer) for ex in ws.exercises]
    if wrong_first:
        answers[0] = str(int(float(ws.exercises[0].answer)) + 1)
    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)
    return ws.instance_id


def test_run_progress_graph_generated_path(monkeypatch, db: Database, tmp_output, child: ChildProfile, make_fake_llm_client):
    _seed_progress(db, child, 1001, wrong_first=True)
    _seed_progress(db, child, 1002)

    fake_json = (
        '{"summary_el":"Καλή σταθερή πορεία.",'
        '"suggestions":[{"target_micro_skill_id":"addition_single_digit",'
        '"suggested_worksheet_type":"drill",'
        '"rationale_el":"Συνέχισε με μικρά βήματα.",'
        '"confidence":"high"}]}'
    )
    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", lambda: make_fake_llm_client(fake_json))

    from app.services.progress_summary_service import build_progress_report

    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "generated"
    assert report.task_id is not None
    assert report.trace_summary["step_names"] == ["grounding", "reasoning", "validation"]


def test_run_review_graph_entrypoint(monkeypatch, db: Database, tmp_output, child: ChildProfile, make_fake_llm_client):
    instance_id = _seed_progress(db, child, 1101, wrong_first=True)
    fake_json = (
        '{"review_summary_el":"Χρειάζεται λίγη ακόμη προσοχή.",'
        '"mistake_types":[{"exercise_id":"placeholder","error_type":"careless","rationale_el":"Μικρή απροσεξία."}],'
        '"next_step_suggestion_el":"Κάντε ακόμη ένα σύντομο φύλλο."}'
    )
    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", lambda: make_fake_llm_client(fake_json))

    from app.services.worksheet_review_service import review_confirmed_worksheet

    outcome = review_confirmed_worksheet(instance_id, db=db)

    assert outcome.narrative_status == "generated"
    assert "Χρειάζεται" in (outcome.summary_el or "")
    assert outcome.trace_summary["step_count"] == 3


def test_run_planning_graph_entrypoint(monkeypatch, db: Database, tmp_output, child: ChildProfile, make_fake_llm_client):
    _seed_progress(db, child, 1201, wrong_first=True)
    fake_json = (
        '{"suggestions":[{"target_micro_skill_id":"addition_single_digit",'
        '"suggested_worksheet_type":"drill",'
        '"rationale_el":"Συνέχισε με στοχευμένη εξάσκηση.",'
        '"confidence":"medium"}]}'
    )
    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", lambda: make_fake_llm_client(fake_json))

    from app.services.tutor_planning_service import plan_next_step

    outcome = plan_next_step(child, db=db)

    assert outcome.narrative_status == "generated"
    assert outcome.suggestions
    assert outcome.suggestions[0]["target_micro_skill_id"] == "addition_single_digit"


def test_progress_graph_repeatable_step_order(monkeypatch, db: Database, tmp_output, child: ChildProfile, make_fake_llm_client):
    _seed_progress(db, child, 1202)

    fake_json = (
        '{"summary_el":"Σταθερή πρόοδος.",'
        '"suggestions":[{"target_micro_skill_id":"addition_single_digit",'
        '"suggested_worksheet_type":"drill",'
        '"rationale_el":"Συνεχίστε με σύντομο φύλλο.",'
        '"confidence":"medium"}]}'
    )
    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", lambda: make_fake_llm_client(fake_json))

    from app.services.progress_summary_service import build_progress_report

    first = build_progress_report(child=child, include_narrative=True, db=db)
    second = build_progress_report(child=child, include_narrative=True, db=db)

    assert first.prompt_version == second.prompt_version == "v1/progress_summary"
    assert first.trace_summary["step_names"] == second.trace_summary["step_names"] == [
        "grounding",
        "reasoning",
        "validation",
    ]



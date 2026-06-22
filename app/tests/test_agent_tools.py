from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.agents.tools import build_manual_review_context, build_next_step_plan_context, build_progress_deterministic_context
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.submission_service import confirm_and_score, set_answers_on_draft, start_submission
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "agent_tools.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_confirmed_sheet(db: Database, child: ChildProfile, seed: int, wrong_first: bool = False) -> str:
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)
    answers = [str(ex.answer) for ex in ws.exercises]
    if wrong_first:
        answers[0] = str(int(float(ws.exercises[0].answer)) + 1)
    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)
    return ws.instance_id


def test_build_progress_deterministic_context_returns_code_owned_metrics(db: Database, tmp_output):
    child = ChildProfile(child_id="tool-child", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, 1401, wrong_first=True)
    context = build_progress_deterministic_context(child=child, limit=20, db=db)

    assert context["child"]["child_id"] == child.child_id
    assert context["worksheet_count"] == 1
    assert context["overall_accuracy_pct"] == 75.0


def test_build_manual_review_context_uses_persisted_snapshot(db: Database, tmp_output):
    child = ChildProfile(child_id="tool-review", display_name="Μαρία", age=10, grade_level=4)
    db.save_child_profile(child)
    instance_id = _seed_confirmed_sheet(db, child, 1402, wrong_first=True)
    context = build_manual_review_context(instance_id=instance_id, db=db)

    assert context["instance_id"] == instance_id
    assert context["entries"]
    assert context["entries"][0]["is_correct"] is False
    assert context["accuracy_pct"] == 75.0


def test_build_next_step_plan_context_includes_progression_decision(db: Database, tmp_output):
    child = ChildProfile(child_id="tool-plan", display_name="Νίκος", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, 1403, wrong_first=True)
    _seed_confirmed_sheet(db, child, 1404)
    _seed_confirmed_sheet(db, child, 1405)

    context = build_next_step_plan_context(child=child, limit=20, db=db)

    assert context["progression_decision"] is not None
    assert "action" in context["progression_decision"]


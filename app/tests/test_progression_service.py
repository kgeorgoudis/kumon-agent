from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.progression_service import evaluate_progression
from app.services.submission_service import confirm_and_score, set_answers_on_draft, start_submission
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "progression.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def child(db: Database) -> ChildProfile:
    profile = ChildProfile(child_id="progress-child", display_name="Παιδί", age=10, grade_level=4)
    db.save_child_profile(profile)
    return profile


def _score_ordering_sheet(db: Database, child: ChildProfile, seed: int, correct: bool) -> None:
    ws = generate_worksheet(MicroSkillId.ORDERING_NUMBERS, child=child, count=5, seed=seed)
    db.save_worksheet_instance(ws)
    submission = start_submission(ws.instance_id, db=db)
    if correct:
        answers = [ex.canonical_answer or "" for ex in ws.exercises]
    else:
        answers = ["999 888 777 666" for _ in ws.exercises]
    set_answers_on_draft(submission.submission_id, answers, db=db)
    confirm_and_score(submission.submission_id, db=db)


def test_progression_advances_after_three_high_accuracy_ordering_sheets(db: Database, tmp_output, child: ChildProfile):
    _score_ordering_sheet(db, child, seed=101, correct=True)
    _score_ordering_sheet(db, child, seed=102, correct=True)
    _score_ordering_sheet(db, child, seed=103, correct=True)

    decision = evaluate_progression(child.child_id, MicroSkillId.ORDERING_NUMBERS, db=db)

    assert decision.action == "advance"
    assert decision.from_micro_skill_id == MicroSkillId.ORDERING_NUMBERS
    assert decision.next_micro_skill_id != MicroSkillId.ORDERING_NUMBERS
    assert decision.accuracy_pct >= 90.0


def test_progression_steps_back_after_three_low_accuracy_ordering_sheets(db: Database, tmp_output, child: ChildProfile):
    _score_ordering_sheet(db, child, seed=201, correct=False)
    _score_ordering_sheet(db, child, seed=202, correct=False)
    _score_ordering_sheet(db, child, seed=203, correct=False)

    decision = evaluate_progression(child.child_id, MicroSkillId.ORDERING_NUMBERS, db=db)

    assert decision.action == "step_back"
    assert decision.from_micro_skill_id == MicroSkillId.ORDERING_NUMBERS
    assert decision.accuracy_pct < 70.0




from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli.main import app
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.submission_service import start_submission, confirm_and_score
from app.services.worksheet_generator import generate_worksheet
import app.config as cfg

runner = CliRunner()


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "cli_pending.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _save_two_worksheets(db: Database):
    ws1 = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=201)
    ws2 = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, count=3, seed=202)
    db.save_worksheet_instance(ws1)
    db.save_worksheet_instance(ws2)
    return ws1, ws2


def test_cli_pending_lists_only_unsubmitted_with_full_ids(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    ws_pending, ws_confirmed = _save_two_worksheets(db)

    submission = start_submission(ws_confirmed.instance_id, db=db)
    answers = [str(ex.answer) for ex in ws_confirmed.exercises]
    from app.services.submission_service import set_answers_on_draft

    set_answers_on_draft(submission.submission_id, answers, db=db)
    confirm_and_score(submission.submission_id, db=db)

    result = runner.invoke(app, ["pending"])

    assert result.exit_code == 0
    assert ws_pending.instance_id in result.output
    assert ws_confirmed.instance_id not in result.output
    assert "Εκκρεμή Φύλλα για Υποβολή" in result.output


def test_cli_pending_empty_message(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    result = runner.invoke(app, ["pending"])

    assert result.exit_code == 0
    assert "Δεν υπάρχουν εκκρεμή φύλλα για υποβολή." in result.output


def test_cli_pending_filters_by_child_name(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)

    child_a = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    child_b = ChildProfile(child_id="kostas", display_name="Κώστας", age=10, grade_level=4)
    db.save_child_profile(child_a)
    db.save_child_profile(child_b)

    ws_a = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child_a, count=2, seed=203)
    ws_b = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child_b, count=2, seed=204)
    db.save_worksheet_instance(ws_a)
    db.save_worksheet_instance(ws_b)

    result = runner.invoke(app, ["pending", "--child", "Ελένη"])

    assert result.exit_code == 0
    assert ws_a.instance_id in result.output
    assert ws_b.instance_id not in result.output


def test_cli_pending_child_filter_no_results_message(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    result = runner.invoke(app, ["pending", "--child", "Άγνωστο"])

    assert result.exit_code == 0
    assert "Δεν υπάρχουν εκκρεμή φύλλα για υποβολή για το παιδί 'Άγνωστο'." in result.output


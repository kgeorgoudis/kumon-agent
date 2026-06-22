from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import app.config as cfg
from app.cli.main import app
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.submission_service import (
    confirm_and_score,
    set_answers_on_draft,
    start_submission,
)
from app.services.worksheet_generator import generate_worksheet

runner = CliRunner()


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "cli_progress.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_confirmed_sheet(db: Database, child: ChildProfile, seed: int, wrong_first: bool = False) -> None:
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)

    answers = [str(ex.answer) for ex in ws.exercises]
    if wrong_first:
        answers[0] = str(int(float(ws.exercises[0].answer)) + 1)
    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)


def test_cli_progress_no_data_message(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)

    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)

    result = runner.invoke(app, ["progress", "--child", "Ελένη", "--no-llm"])

    assert result.exit_code == 0
    assert "Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα για αναφορά προόδου." in result.output


def test_cli_progress_deterministic_output(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)

    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, seed=701, wrong_first=True)
    _seed_confirmed_sheet(db, child, seed=702, wrong_first=False)

    result = runner.invoke(app, ["progress", "--child", "Ελένη", "--no-llm"])

    assert result.exit_code == 0
    assert "Αναφορά Προόδου" in result.output
    assert "Συνολική ακρίβεια" in result.output
    assert "addition_single_digit" in result.output


def test_cli_progress_llm_degraded_warning(db: Database, tmp_output, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)

    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, seed=801)
    _seed_confirmed_sheet(db, child, seed=802, wrong_first=True)

    def _raise_client():
        raise RuntimeError("offline")

    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", _raise_client)

    result = runner.invoke(app, ["progress", "--child", "Ελένη"])

    assert result.exit_code == 0
    assert "Η αφήγηση LLM δεν ήταν διαθέσιμη" in result.output


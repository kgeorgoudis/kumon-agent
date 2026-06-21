from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli.main import app
from app.domain.models import MicroSkillId
from app.persistence.database import Database
from app.services.worksheet_generator import generate_worksheet
import app.config as cfg

runner = CliRunner()


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "cli_submit.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def worksheet(db: Database, tmp_output):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=77)
    db.save_worksheet_instance(ws)
    return ws


@pytest.fixture()
def ordering_worksheet(db: Database, tmp_output):
    ws = generate_worksheet(MicroSkillId.ORDERING_NUMBERS, count=3, seed=55)
    db.save_worksheet_instance(ws)
    return ws


def test_cli_app_starts_for_submit_scaffold():
    """CLI boots and shows help with submit command listed."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "submit" in result.output


# ── US1 CLI tests ─────────────────────────────────────────────────────────────

def test_cli_submit_unknown_worksheet_exits_1(db: Database, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    result = runner.invoke(app, ["submit", "does-not-exist", "--answers", "1,2,3"])
    assert result.exit_code == 1
    assert "ERR_WORKSHEET_NOT_FOUND" in result.output


def test_cli_submit_bulk_wrong_count_exits_1(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    # worksheet has 3 exercises, only 2 answers provided
    result = runner.invoke(
        app,
        ["submit", worksheet.instance_id, "--answers", "1,2", "--no-confirm"],
    )
    assert result.exit_code == 1
    assert "ERR_ANSWER_COUNT_MISMATCH" in result.output


def test_cli_submit_bulk_correct_answers_scores_100(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    correct = ",".join(str(ex.answer) for ex in worksheet.exercises)
    result = runner.invoke(
        app,
        ["submit", worksheet.instance_id, "--answers", correct, "--no-confirm"],
    )
    assert result.exit_code == 0
    assert "100.0%" in result.output


def test_cli_submit_duplicate_confirmed_exits_1(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    correct = ",".join(str(ex.answer) for ex in worksheet.exercises)
    # First submission succeeds
    runner.invoke(app, ["submit", worksheet.instance_id, "--answers", correct, "--no-confirm"])
    # Second should fail
    result = runner.invoke(
        app,
        ["submit", worksheet.instance_id, "--answers", correct, "--no-confirm"],
    )
    assert result.exit_code == 1
    assert "ERR_SUBMISSION_ALREADY_CONFIRMED" in result.output


# ── US2 CLI tests ──────────────────────────────────────��──────────────────────

def test_cli_submit_resume_no_draft_exits_1(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    result = runner.invoke(app, ["submit", worksheet.instance_id, "--resume", "--answers", "1,2,3"])
    assert result.exit_code == 1
    assert "ERR_DRAFT_NOT_FOUND" in result.output


# ── US3 CLI tests ─────────────────────────────────────────────────────────────

def test_cli_submit_invalid_time_format_exits_1(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    correct = ",".join(str(ex.answer) for ex in worksheet.exercises)
    result = runner.invoke(
        app,
        ["submit", worksheet.instance_id, "--answers", correct, "--time", "99:99", "--no-confirm"],
    )
    assert result.exit_code == 1
    assert "ERR_INVALID_DURATION_FORMAT" in result.output


def test_cli_submit_with_valid_time_shows_in_output(db: Database, worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    correct = ",".join(str(ex.answer) for ex in worksheet.exercises)
    result = runner.invoke(
        app,
        ["submit", worksheet.instance_id, "--answers", correct, "--time", "5m", "--no-confirm"],
    )
    assert result.exit_code == 0
    # 5 minutes = 300 seconds = displayed as 5:00
    assert "5:00" in result.output


def test_cli_submit_ordering_bulk_semicolon_scores_100(db: Database, ordering_worksheet, monkeypatch):
    monkeypatch.setattr("app.cli.main.default_db", db)
    answers = "; ".join(ex.canonical_answer or "" for ex in ordering_worksheet.exercises)
    result = runner.invoke(
        app,
        ["submit", ordering_worksheet.instance_id, "--answers", answers, "--no-confirm"],
    )
    assert result.exit_code == 0
    assert "100.0%" in result.output



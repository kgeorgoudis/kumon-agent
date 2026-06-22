from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.progress_summary_service import build_progress_report
from app.services.submission_service import confirm_and_score, set_answers_on_draft, start_submission
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "agent_fallback.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_confirmed_sheet(db: Database, child: ChildProfile, seed: int) -> None:
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)
    answers = [str(ex.answer) for ex in ws.exercises]
    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)


def test_progress_graph_fallback_on_unavailable_model(monkeypatch, db: Database, tmp_output):
    child = ChildProfile(child_id="fallback-1", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, 1301)

    def _raise_client():
        raise RuntimeError("offline")

    monkeypatch.setattr("app.agents.agent_graph.get_llm_client", _raise_client)
    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "degraded"
    assert report.llm_error_code == "ERR_LLM_UNAVAILABLE"


def test_progress_graph_fallback_on_invalid_json(monkeypatch, db: Database, tmp_output, make_fake_llm_client):
    child = ChildProfile(child_id="fallback-2", display_name="Μαρία", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, 1302)

    monkeypatch.setattr(
        "app.agents.agent_graph.get_llm_client",
        lambda: make_fake_llm_client("not-json"),
    )
    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "degraded"
    assert report.llm_error_code == "ERR_LLM_INVALID_JSON"


def test_progress_graph_fallback_on_truncated_output(monkeypatch, db: Database, tmp_output, make_fake_llm_client):
    child = ChildProfile(child_id="fallback-3", display_name="Νίκος", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, 1303)

    monkeypatch.setattr(
        "app.agents.agent_graph.get_llm_client",
        lambda: make_fake_llm_client("{}", finish_reason="length"),
    )
    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "degraded"
    assert report.llm_error_code == "ERR_LLM_TRUNCATED"


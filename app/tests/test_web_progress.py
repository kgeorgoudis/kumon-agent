from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.config as cfg
from app.api import api
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.progress_summary_service import build_progress_report
from app.services.submission_service import (
    confirm_and_score,
    set_answers_on_draft,
    start_submission,
)
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "web_progress.db")


@pytest.fixture()
def test_client(db: Database, tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    monkeypatch.setattr("app.api.default_db", db)
    return TestClient(api)


def _seed_confirmed_sheet(db: Database, child: ChildProfile, seed: int, wrong_first: bool = False) -> None:
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)

    answers = [str(ex.answer) for ex in ws.exercises]
    if wrong_first:
        answers[0] = str(int(float(ws.exercises[0].answer)) + 1)

    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)


def test_progress_page_with_data(test_client: TestClient, db: Database):
    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, seed=901)
    _seed_confirmed_sheet(db, child, seed=902, wrong_first=True)

    response = test_client.get("/progress", params={"child": "Ελένη", "llm": "false"})

    assert response.status_code == 200
    assert "Αναφορά Προόδου" in response.text
    assert "Ελένη" in response.text
    assert "Συνολική ακρίβεια" in response.text


def test_progress_page_empty_state(test_client: TestClient, db: Database):
    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)

    response = test_client.get("/progress", params={"child": "Ελένη", "llm": "false"})

    assert response.status_code == 200
    assert "Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα" in response.text


def test_progress_page_degraded_mode_banner(test_client: TestClient, db: Database, monkeypatch):
    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, seed=903)
    _seed_confirmed_sheet(db, child, seed=904, wrong_first=True)

    def _raise_client():
        raise RuntimeError("offline")

    monkeypatch.setattr("app.services.progress_summary_service.get_llm_client", _raise_client)

    response = test_client.get("/progress", params={"child": "Ελένη", "llm": "true"})

    assert response.status_code == 200
    assert "Η αφήγηση LLM δεν ήταν διαθέσιμη" in response.text


def test_progress_page_parity_with_service_payload(test_client: TestClient, db: Database):
    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, seed=905)
    _seed_confirmed_sheet(db, child, seed=906, wrong_first=True)

    report = build_progress_report(child=child, include_narrative=False, db=db)
    response = test_client.get("/progress", params={"child": "Ελένη", "llm": "false"})

    assert response.status_code == 200
    assert str(report.worksheet_count) in response.text
    assert f"{report.overall_accuracy_pct:.1f}%" in response.text
    if report.skill_progress:
        assert report.skill_progress[0].micro_skill_id in response.text



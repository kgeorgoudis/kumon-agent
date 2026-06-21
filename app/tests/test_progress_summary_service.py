from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import ChildProfile, MicroSkillId
from app.persistence.database import Database
from app.services.progress_summary_service import (
    build_progress_report,
    classify_accuracy_trend,
    load_progress_prompt,
)
from app.services.submission_service import (
    confirm_and_score,
    set_answers_on_draft,
    start_submission,
)
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "progress_summary.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_confirmed_sheet(
    db: Database,
    child: ChildProfile,
    skill: MicroSkillId,
    seed: int,
    wrong_slots: set[int] | None = None,
) -> None:
    ws = generate_worksheet(skill, child=child, count=4, seed=seed)
    db.save_worksheet_instance(ws)
    sub = start_submission(ws.instance_id, db=db)

    wrong_slots = wrong_slots or set()
    answers: list[str] = []
    for idx, ex in enumerate(ws.exercises):
        if idx in wrong_slots:
            answers.append(str(int(float(ex.answer)) + 1))
        else:
            answers.append(str(ex.answer))

    set_answers_on_draft(sub.submission_id, answers, db=db)
    confirm_and_score(sub.submission_id, db=db)


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):
        message = type("M", (), {"content": self._content})
        choice = type("C", (), {"message": message})
        return type("R", (), {"choices": [choice]})


class _FakeClient:
    def __init__(self, content: str):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(content)})


def test_classify_accuracy_trend_insufficient_data():
    assert classify_accuracy_trend([95.0]) == "insufficient_data"


def test_classify_accuracy_trend_improving():
    assert classify_accuracy_trend([50.0, 55.0, 80.0, 90.0]) == "improving"


def test_classify_accuracy_trend_stable():
    assert classify_accuracy_trend([80.0, 82.0, 81.0, 83.0]) == "stable"


def test_build_progress_report_deterministic_without_llm(db: Database, tmp_output):
    child = ChildProfile(child_id="eleni", display_name="Ελένη", age=10, grade_level=4)
    db.save_child_profile(child)

    _seed_confirmed_sheet(db, child, MicroSkillId.ADDITION_SINGLE_DIGIT, seed=401, wrong_slots={0, 1})
    _seed_confirmed_sheet(db, child, MicroSkillId.ADDITION_SINGLE_DIGIT, seed=402, wrong_slots={0})
    _seed_confirmed_sheet(db, child, MicroSkillId.MULTIPLICATION_2_5, seed=403, wrong_slots=set())

    report = build_progress_report(child=child, include_narrative=False, db=db)

    assert report.worksheet_count == 3
    assert report.date_from is not None
    assert report.date_to is not None
    assert report.narrative_status == "not_requested"
    assert len(report.skill_progress) == 2


def test_build_progress_report_no_data_message(db: Database, tmp_output):
    child = ChildProfile(child_id="no-data", display_name="Κανένα", age=10, grade_level=4)
    db.save_child_profile(child)

    report = build_progress_report(child=child, include_narrative=False, db=db)

    assert report.worksheet_count == 0
    assert "Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα" in (report.summary_el or "")


def test_build_progress_report_llm_success(monkeypatch, db: Database, tmp_output):
    child = ChildProfile(child_id="llm-ok", display_name="Μαρία", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, MicroSkillId.ADDITION_SINGLE_DIGIT, seed=501)
    _seed_confirmed_sheet(db, child, MicroSkillId.ADDITION_SINGLE_DIGIT, seed=502, wrong_slots={0})

    fake_json = (
        '{"summary_el":"Καλή πορεία συνολικά.",' 
        '"suggestions":[{"target_micro_skill_id":"addition_single_digit",' 
        '"suggested_worksheet_type":"drill",' 
        '"rationale_el":"Δουλέψτε λίγο ακόμη πρόσθεση μονοψήφιων.",' 
        '"confidence":"high"}]}'
    )
    monkeypatch.setattr(
        "app.services.progress_summary_service.get_llm_client",
        lambda: _FakeClient(fake_json),
    )

    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "generated"
    assert "Καλή πορεία" in (report.summary_el or "")
    assert report.suggestions
    assert report.suggestions[0].target_micro_skill_id == "addition_single_digit"


def test_build_progress_report_llm_unavailable_fallback(monkeypatch, db: Database, tmp_output):
    child = ChildProfile(child_id="llm-fail", display_name="Νίκος", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, MicroSkillId.MULTIPLICATION_2_5, seed=601, wrong_slots={0, 1})
    _seed_confirmed_sheet(db, child, MicroSkillId.MULTIPLICATION_2_5, seed=602, wrong_slots={0})

    def _raise_client():
        raise RuntimeError("offline")

    monkeypatch.setattr("app.services.progress_summary_service.get_llm_client", _raise_client)

    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "degraded"
    assert report.llm_error_code == "ERR_LLM_UNAVAILABLE"
    assert report.suggestions


def test_load_progress_prompt_includes_kumon_tutor_persona():
    prompt = load_progress_prompt()
    assert "Prompt: kumon_tutor_persona - v1" in prompt
    assert "έμπειρος/η εκπαιδευτικός Kumon" in prompt


def test_build_progress_report_invalid_worksheet_type_is_sanitized(monkeypatch, db: Database, tmp_output):
    child = ChildProfile(child_id="llm-sanitize", display_name="Άννα", age=10, grade_level=4)
    db.save_child_profile(child)
    _seed_confirmed_sheet(db, child, MicroSkillId.ADDITION_SINGLE_DIGIT, seed=701)

    fake_json = (
        '{"summary_el":"Υπάρχει πρόοδος.",'
        '"suggestions":[{"target_micro_skill_id":"addition_single_digit",'
        '"suggested_worksheet_type":"free_chat",'
        '"rationale_el":"Συνέχισε σταδιακά.",'
        '"confidence":"medium"}]}'
    )
    monkeypatch.setattr(
        "app.services.progress_summary_service.get_llm_client",
        lambda: _FakeClient(fake_json),
    )

    report = build_progress_report(child=child, include_narrative=True, db=db)

    assert report.narrative_status == "generated"
    assert report.suggestions
    assert report.suggestions[0].suggested_worksheet_type is None



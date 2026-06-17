"""
Tests for app/persistence/database.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.models import (
    ChildProfile,
    MicroSkillId,
    OcrField,
    OcrResult,
    OcrValueSource,
    SubmissionStatus,
    WorksheetSubmission,
)
from app.persistence.database import Database
from app.services.worksheet_generator import generate_worksheet
import app.config as cfg


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Return an isolated in-memory database for each test."""
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def child() -> ChildProfile:
    return ChildProfile(
        child_id="test-001",
        display_name="Γιώργης",
        age=10,
        grade_level=4,
    )


def test_save_and_retrieve_child_profile(db, child):
    db.save_child_profile(child)
    retrieved = db.get_child_profile(child.child_id)
    assert retrieved is not None
    assert retrieved.display_name == child.display_name
    assert retrieved.age == child.age


def test_update_child_profile(db, child):
    db.save_child_profile(child)
    updated = child.model_copy(update={"age": 11})
    db.save_child_profile(updated)
    retrieved = db.get_child_profile(child.child_id)
    assert retrieved.age == 11


def test_list_child_profiles_empty(db):
    assert db.list_child_profiles() == []


def test_list_child_profiles(db, child):
    db.save_child_profile(child)
    profiles = db.list_child_profiles()
    assert len(profiles) == 1
    assert profiles[0].child_id == child.child_id


def test_save_worksheet_instance(db, tmp_output, child):
    db.save_child_profile(child)
    instance = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, child=child, seed=1)
    db.save_worksheet_instance(instance)
    retrieved = db.get_worksheet_instance(instance.instance_id)
    assert retrieved is not None
    assert retrieved.micro_skill_id == MicroSkillId.MULTIPLICATION_2_5
    assert len(retrieved.exercises) == len(instance.exercises)


def test_get_worksheet_instance_not_found(db):
    assert db.get_worksheet_instance("nonexistent") is None


def test_save_is_idempotent(db, tmp_output, child):
    """Saving the same worksheet twice should not raise."""
    db.save_child_profile(child)
    instance = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, seed=0)
    db.save_worksheet_instance(instance)
    db.save_worksheet_instance(instance)  # should not raise


def test_get_recent_worksheets(db, tmp_output, child):
    db.save_child_profile(child)
    for seed in range(5):
        inst = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, child=child, seed=seed)
        db.save_worksheet_instance(inst)
    sheets = db.get_recent_worksheets(child_id=child.child_id, limit=3)
    assert len(sheets) == 3


def test_filter_by_micro_skill(db, tmp_output, child):
    db.save_child_profile(child)
    mult = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, child=child, seed=0)
    add = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, child=child, seed=0)
    db.save_worksheet_instance(mult)
    db.save_worksheet_instance(add)
    sheets = db.get_recent_worksheets(micro_skill_id=MicroSkillId.MULTIPLICATION_2_5)
    assert all(s.micro_skill_id == MicroSkillId.MULTIPLICATION_2_5 for s in sheets)


def test_submission_status_transition_to_ocr_processed(db, tmp_output):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=3)
    db.save_worksheet_instance(ws)

    submission = WorksheetSubmission(
        instance_id=ws.instance_id,
        file_path="/tmp/sub.jpg",
        mime_type="image/jpeg",
        file_hash="abc123",
    )
    db.save_worksheet_submission(submission)
    db.update_submission_status(submission.submission_id, SubmissionStatus.OCR_PROCESSED)

    fetched = db.get_submission(submission.submission_id)
    assert fetched is not None
    assert fetched.status == SubmissionStatus.OCR_PROCESSED


def test_save_and_get_ocr_result_and_fields(db, tmp_output):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=5)
    db.save_worksheet_instance(ws)

    submission = WorksheetSubmission(
        instance_id=ws.instance_id,
        file_path="/tmp/sub.jpg",
        mime_type="image/jpeg",
        file_hash="hash",
    )
    db.save_worksheet_submission(submission)

    result = OcrResult(
        submission_id=submission.submission_id,
        instance_id=ws.instance_id,
        overall_confidence=0.9,
    )
    db.save_ocr_result(result)

    fields = [
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[0].exercise_id,
            slot_index=0,
            raw_value="12",
            confidence=0.95,
            needs_review=False,
        ),
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[1].exercise_id,
            slot_index=1,
            raw_value="?",
            confidence=0.2,
            needs_review=True,
        ),
    ]
    db.save_ocr_fields(fields)

    fetched_result = db.get_ocr_result(result.ocr_result_id)
    assert fetched_result is not None

    fetched_fields = db.get_ocr_fields(result.ocr_result_id)
    assert len(fetched_fields) == 2
    assert fetched_fields[0].slot_index == 0
    assert fetched_fields[1].needs_review is True

    db.update_ocr_field_correction(fetched_fields[1].ocr_field_id, "34", OcrValueSource.MANUAL)
    corrected = db.get_ocr_fields(result.ocr_result_id)[1]
    assert corrected.corrected_value == "34"
    assert corrected.value_source == OcrValueSource.MANUAL

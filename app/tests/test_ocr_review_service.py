from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import MicroSkillId, OcrField, OcrResult, OcrResultStatus, SubmissionStatus, WorksheetSubmission
from app.persistence.database import Database
from app.services.ocr_review_service import (
    OcrFieldNotFoundError,
    OcrResultNotFoundError,
    ReviewNotCompleteError,
    approve_ocr_result,
    correct_ocr_field,
    list_ocr_fields,
)
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_ocr(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=13)
    db.save_worksheet_instance(ws)

    submission = WorksheetSubmission(
        instance_id=ws.instance_id,
        file_path="/tmp/sub.jpg",
        mime_type="image/jpeg",
        file_hash="hash",
        status=SubmissionStatus.OCR_PROCESSED,
    )
    db.save_worksheet_submission(submission)

    result = OcrResult(
        submission_id=submission.submission_id,
        instance_id=ws.instance_id,
        overall_confidence=0.75,
        status=OcrResultStatus.NEEDS_REVIEW,
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
            raw_value="1?",
            confidence=0.20,
            needs_review=True,
        ),
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[2].exercise_id,
            slot_index=2,
            raw_value="34",
            confidence=0.80,
            needs_review=True,
        ),
    ]
    db.save_ocr_fields(fields)
    return submission, result, ws, fields


def test_list_review_fields_sorted_and_present(db, tmp_output):
    _, result, _, _ = _seed_ocr(db)

    fields = list_ocr_fields(result.ocr_result_id, db=db)
    assert len(fields) == 3
    assert [f.slot_index for f in fields] == [0, 1, 2]


def test_list_review_fields_missing_result_raises(db):
    with pytest.raises(OcrResultNotFoundError):
        list_ocr_fields("missing", db=db)


def test_correct_field_sets_manual_source(db, tmp_output):
    _, result, ws, _ = _seed_ocr(db)

    target_ex = ws.exercises[1].exercise_id
    correct_ocr_field(result.ocr_result_id, target_ex, "19", db=db)

    fields = db.get_ocr_fields(result.ocr_result_id)
    corrected = [f for f in fields if f.exercise_id == target_ex][0]
    assert corrected.corrected_value == "19"
    assert corrected.value_source.value == "manual"
    assert corrected.original_ocr_value == "1?"


def test_correct_field_missing_exercise_raises(db, tmp_output):
    _, result, _, _ = _seed_ocr(db)

    with pytest.raises(OcrFieldNotFoundError):
        correct_ocr_field(result.ocr_result_id, "missing-exercise", "10", db=db)


def test_approve_transitions_result_and_submission_status(db, tmp_output):
    submission, result, _, _ = _seed_ocr(db)

    approve_ocr_result(result.ocr_result_id, db=db)

    fetched_result = db.get_ocr_result(result.ocr_result_id)
    assert fetched_result is not None
    assert fetched_result.status.value == "reviewed"

    fetched_submission = db.get_submission(submission.submission_id)
    assert fetched_submission is not None
    assert fetched_submission.status.value == "reviewed"


def test_approve_mismatched_requires_completed_fields(db, tmp_output):
    _, result, _, _ = _seed_ocr(db)

    db.transition_ocr_result_status(result.ocr_result_id, OcrResultStatus.REVIEWED)
    with db.connect() as conn:
        conn.execute(
            "UPDATE ocr_results SET status = ? WHERE ocr_result_id = ?",
            (OcrResultStatus.MISMATCHED.value, result.ocr_result_id),
        )
        conn.execute(
            "UPDATE ocr_fields SET raw_value = '' WHERE ocr_result_id = ? AND slot_index = 1",
            (result.ocr_result_id,),
        )

    with pytest.raises(ReviewNotCompleteError):
        approve_ocr_result(result.ocr_result_id, db=db)



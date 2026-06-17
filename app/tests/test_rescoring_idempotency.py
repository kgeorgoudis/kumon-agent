from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import MicroSkillId, OcrField, OcrResult, OcrResultStatus, SubmissionStatus, WorksheetSubmission
from app.persistence.database import Database
from app.services.scoring_service import (
    RescoreFailedOcrError,
    RescoreMismatchedError,
    RescoreNotReadyError,
    RescoreResultNotFoundError,
    build_rescoring_input_hash,
    normalize_reviewed_fields,
    rescore_ocr_result,
)
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


def _seed_reviewed_ocr(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=44)
    db.save_worksheet_instance(ws)

    submission = WorksheetSubmission(
        instance_id=ws.instance_id,
        file_path="/tmp/sub.jpg",
        mime_type="image/jpeg",
        file_hash="hash",
        status=SubmissionStatus.REVIEWED,
    )
    db.save_worksheet_submission(submission)

    result = OcrResult(
        submission_id=submission.submission_id,
        instance_id=ws.instance_id,
        overall_confidence=0.8,
        status=OcrResultStatus.REVIEWED,
    )
    db.save_ocr_result(result)

    fields = [
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[0].exercise_id,
            slot_index=0,
            raw_value="12",
            confidence=0.9,
            needs_review=False,
        ),
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[1].exercise_id,
            slot_index=1,
            raw_value="",
            corrected_value="19",
            confidence=0.4,
            needs_review=True,
        ),
        OcrField(
            ocr_result_id=result.ocr_result_id,
            exercise_id=ws.exercises[2].exercise_id,
            slot_index=2,
            raw_value="34",
            confidence=0.8,
            needs_review=False,
        ),
    ]
    db.save_ocr_fields(fields)
    return result


def test_normalized_hash_is_deterministic_for_same_input_order():
    fields_a = [
        {"exercise_id": "b", "slot_index": 1, "raw_value": "2", "corrected_value": "", "value_source": "ocr", "needs_review": False},
        {"exercise_id": "a", "slot_index": 0, "raw_value": "1", "corrected_value": "", "value_source": "ocr", "needs_review": False},
    ]
    fields_b = list(reversed(fields_a))

    h1 = build_rescoring_input_hash("ws", "ocr", fields_a)
    h2 = build_rescoring_input_hash("ws", "ocr", fields_b)
    assert h1 == h2


def test_rescore_raises_when_result_missing(db):
    with pytest.raises(RescoreResultNotFoundError):
        rescore_ocr_result("missing", db=db)


def test_rescore_raises_when_not_reviewed(db, tmp_output):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=1)
    db.save_worksheet_instance(ws)

    submission = WorksheetSubmission(
        instance_id=ws.instance_id,
        file_path="/tmp/sub.jpg",
        mime_type="image/jpeg",
        file_hash="h",
        status=SubmissionStatus.OCR_PROCESSED,
    )
    db.save_worksheet_submission(submission)

    result = OcrResult(
        submission_id=submission.submission_id,
        instance_id=ws.instance_id,
        overall_confidence=0.7,
    )
    db.save_ocr_result(result)

    with pytest.raises(RescoreNotReadyError):
        rescore_ocr_result(result.ocr_result_id, db=db)


def test_rescore_is_idempotent_for_identical_reviewed_input(db, tmp_output):
    result = _seed_reviewed_ocr(db)

    snap1 = rescore_ocr_result(result.ocr_result_id, db=db)
    snap2 = rescore_ocr_result(result.ocr_result_id, db=db)

    assert snap1.input_hash == snap2.input_hash
    assert snap1.accuracy_pct == snap2.accuracy_pct
    assert snap1.details_json == snap2.details_json

    snapshots = db.list_score_snapshots(result.ocr_result_id)
    assert len(snapshots) == 1

    fetched = db.get_ocr_result(result.ocr_result_id)
    assert fetched is not None
    assert fetched.status == OcrResultStatus.SCORED


def test_rescore_blocks_failed_ocr_status(db, tmp_output):
    result = _seed_reviewed_ocr(db)
    with db.connect() as conn:
        conn.execute(
            "UPDATE ocr_results SET status = ? WHERE ocr_result_id = ?",
            (OcrResultStatus.FAILED.value, result.ocr_result_id),
        )

    with pytest.raises(RescoreFailedOcrError):
        rescore_ocr_result(result.ocr_result_id, db=db)


def test_rescore_blocks_mismatched_ocr_status(db, tmp_output):
    result = _seed_reviewed_ocr(db)
    with db.connect() as conn:
        conn.execute(
            "UPDATE ocr_results SET status = ? WHERE ocr_result_id = ?",
            (OcrResultStatus.MISMATCHED.value, result.ocr_result_id),
        )

    with pytest.raises(RescoreMismatchedError):
        rescore_ocr_result(result.ocr_result_id, db=db)


def test_normalize_reviewed_fields_prefers_corrected_values():
    fields = [
        {
            "exercise_id": "ex1",
            "slot_index": 0,
            "raw_value": "17",
            "corrected_value": "19",
            "value_source": "manual",
            "needs_review": True,
        }
    ]
    normalized = normalize_reviewed_fields(fields)
    assert normalized[0]["value"] == "19"


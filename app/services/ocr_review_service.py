"""OCR review and correction service."""

from __future__ import annotations

from app.domain.models import OcrResultStatus, OcrValueSource, SubmissionStatus
from app.persistence.database import Database, default_db


class OcrResultNotFoundError(RuntimeError):
    code = "ERR_OCR_RESULT_NOT_FOUND"


class ReviewNotCompleteError(RuntimeError):
    code = "ERR_REVIEW_NOT_COMPLETE"


class OcrFieldNotFoundError(RuntimeError):
    code = "ERR_OCR_FIELD_NOT_FOUND"


def list_ocr_fields(ocr_result_id: str, db: Database = default_db):
    """Return OCR fields for display in CLI review command."""
    result = db.get_ocr_result(ocr_result_id)
    if result is None:
        raise OcrResultNotFoundError(f"OCR result not found: {ocr_result_id}")

    fields = db.get_ocr_fields(ocr_result_id)
    if not fields:
        raise OcrResultNotFoundError(f"OCR result not found: {ocr_result_id}")
    return fields


def correct_ocr_field(ocr_result_id: str, exercise_id: str, value: str, db: Database = default_db) -> None:
    """Persist one manual correction for a specific exercise in an OCR result."""
    fields = db.get_ocr_fields(ocr_result_id)
    target = next((f for f in fields if f.exercise_id == exercise_id), None)
    if target is None:
        raise OcrFieldNotFoundError(
            f"No OCR field found for exercise '{exercise_id}' in result '{ocr_result_id}'"
        )

    db.update_ocr_field_correction(
        ocr_field_id=target.ocr_field_id,
        corrected_value=value,
        value_source=OcrValueSource.MANUAL,
    )


def approve_ocr_result(ocr_result_id: str, db: Database = default_db) -> None:
    """Mark OCR result as reviewed and ready for deterministic scoring."""
    result = db.get_ocr_result(ocr_result_id)
    if result is None:
        raise OcrResultNotFoundError(f"OCR result not found: {ocr_result_id}")

    if result.status not in {OcrResultStatus.NEEDS_REVIEW, OcrResultStatus.MISMATCHED}:
        raise ReviewNotCompleteError(f"OCR result not ready for approval: {result.status.value}")

    fields = db.get_ocr_fields(ocr_result_id)
    worksheet = db.get_worksheet_instance(result.instance_id)
    if worksheet is None:
        raise ReviewNotCompleteError(f"Worksheet missing for OCR result: {result.instance_id}")

    if result.status == OcrResultStatus.MISMATCHED:
        if len(fields) != len(worksheet.exercises):
            raise ReviewNotCompleteError("Mismatched OCR field count is still unresolved.")
        for field in fields:
            effective_value = field.corrected_value if field.corrected_value is not None else field.raw_value
            if effective_value in {None, ""}:
                raise ReviewNotCompleteError("Mismatched OCR fields must be manually completed before approval.")

    db.mark_ocr_result_reviewed(ocr_result_id)
    db.update_submission_status(result.submission_id, SubmissionStatus.REVIEWED)


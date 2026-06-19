"""Deterministic rescoring service for reviewed OCR fields."""

from __future__ import annotations

import hashlib
import json

from app.domain.models import OcrResultStatus, ScoreResultSnapshot
from app.persistence.database import Database, default_db


class RescoreError(RuntimeError):
    """Base exception for rescoring failures."""


class RescoreResultNotFoundError(RescoreError):
    code = "ERR_OCR_RESULT_NOT_FOUND"


class RescoreNotReadyError(RescoreError):
    code = "ERR_REVIEW_NOT_COMPLETE"


class RescoreMismatchedError(RescoreError):
    code = "ERR_OCR_MISMATCHED"


class RescoreFailedOcrError(RescoreError):
    code = "ERR_OCR_FAILED"


def normalize_reviewed_fields(fields: list[dict]) -> list[dict]:
    """Normalize reviewed field payload for deterministic hashing and scoring."""
    normalized: list[dict] = []
    for f in fields:
        value = f.get("corrected_value") if f.get("corrected_value") not in (None, "") else f.get("raw_value", "")
        normalized.append(
            {
                "exercise_id": f.get("exercise_id", ""),
                "slot_index": int(f.get("slot_index", 0)),
                "value": str(value or "").strip(),
                "source": f.get("value_source", "ocr"),
                "needs_review": bool(f.get("needs_review", False)),
            }
        )
    return sorted(normalized, key=lambda x: (x["slot_index"], x["exercise_id"]))


def build_rescoring_input_hash(instance_id: str, ocr_result_id: str, fields: list[dict]) -> str:
    """Build a stable hash for idempotent rescoring snapshots."""
    normalized_fields = normalize_reviewed_fields(fields)
    payload = {
        "instance_id": instance_id,
        "ocr_result_id": ocr_result_id,
        "fields": normalized_fields,
    }
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_manual_entries(entries: list[dict]) -> list[dict]:
    """Normalize manual answer entries for deterministic manual scoring hashes."""
    normalized: list[dict] = []
    for entry in entries:
        normalized.append(
            {
                "exercise_id": entry.get("exercise_id", ""),
                "slot_index": int(entry.get("slot_index", 0)),
                "raw_value": str(entry.get("raw_value", "")).strip(),
                "normalized_value": str(entry.get("normalized_value", "")).strip(),
                "is_valid": bool(entry.get("is_valid", False)),
            }
        )
    return sorted(normalized, key=lambda x: (x["slot_index"], x["exercise_id"]))


def build_manual_submission_input_hash(instance_id: str, submission_id: str, entries: list[dict]) -> str:
    """Build a stable hash for deterministic manual submission scoring input."""
    payload = {
        "instance_id": instance_id,
        "submission_id": submission_id,
        "entries": normalize_manual_entries(entries),
    }
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def persist_score_snapshot(
    instance_id: str,
    ocr_result_id: str,
    accuracy_pct: float,
    details: dict,
    db: Database = default_db,
) -> ScoreResultSnapshot:
    """Persist an immutable score snapshot.

    Full scoring computation is introduced in later phase tasks; this function
    currently provides deterministic snapshot persistence scaffolding.
    """
    field_records = details.get("fields", [])
    input_hash = build_rescoring_input_hash(instance_id, ocr_result_id, field_records)
    snapshot = ScoreResultSnapshot(
        instance_id=instance_id,
        ocr_result_id=ocr_result_id,
        input_hash=input_hash,
        accuracy_pct=accuracy_pct,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.save_score_snapshot(snapshot)
    return snapshot


def persist_manual_submission_snapshot(
    *,
    instance_id: str,
    submission_id: str,
    accuracy_pct: float,
    details: dict,
    db: Database = default_db,
) -> ScoreResultSnapshot:
    """Persist immutable score snapshot keyed by manual submission input hash."""
    entries = details.get("entries", [])
    input_hash = build_manual_submission_input_hash(instance_id, submission_id, entries)
    existing = db.get_score_snapshot_by_submission_hash(submission_id, input_hash)
    if existing is not None:
        return existing

    snapshot = ScoreResultSnapshot(
        instance_id=instance_id,
        ocr_result_id=None,
        submission_id=submission_id,
        input_hash=input_hash,
        accuracy_pct=accuracy_pct,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.save_score_snapshot(snapshot)
    return snapshot


def rescore_ocr_result(
    ocr_result_id: str,
    db: Database = default_db,
) -> ScoreResultSnapshot:
    """Deterministically rescore one reviewed OCR result.

    Phase-5 behavior:
    - Requires OCR result status in {reviewed, scored}.
    - Explicitly blocks OCR status failed/mismatched.
    - Builds stable input hash from normalized reviewed field values.
    - Reuses existing snapshot if same hash already exists (idempotent).
    - Computes simple deterministic correctness metric placeholder where
      non-empty values count as answered and contributes to accuracy.
    """
    result = db.get_ocr_result(ocr_result_id)
    if result is None:
        raise RescoreResultNotFoundError(f"OCR result not found: {ocr_result_id}")

    if result.status == OcrResultStatus.FAILED:
        raise RescoreFailedOcrError(f"OCR result failed and cannot be scored: {ocr_result_id}")
    if result.status == OcrResultStatus.MISMATCHED:
        raise RescoreMismatchedError(f"OCR result mismatched and requires review completion: {ocr_result_id}")
    if result.status not in {OcrResultStatus.REVIEWED, OcrResultStatus.SCORED}:
        raise RescoreNotReadyError(f"OCR result is not reviewed: {ocr_result_id}")

    raw_fields = db.get_ocr_fields(ocr_result_id)
    field_dicts = [f.model_dump(mode="json") for f in raw_fields]
    normalized_fields = normalize_reviewed_fields(field_dicts)
    input_hash = build_rescoring_input_hash(result.instance_id, ocr_result_id, normalized_fields)

    existing = db.get_score_snapshot_by_hash(ocr_result_id, input_hash)
    if existing is not None:
        if result.status == OcrResultStatus.REVIEWED:
            db.transition_ocr_result_status(ocr_result_id, OcrResultStatus.SCORED)
        return existing

    total = len(normalized_fields)
    answered = sum(1 for f in normalized_fields if f["value"] != "")
    accuracy_pct = (answered / total * 100.0) if total else 0.0

    details = {
        "fields": normalized_fields,
        "answered": answered,
        "total": total,
        "mode": "phase5_placeholder_scoring",
    }

    snapshot = persist_score_snapshot(
        instance_id=result.instance_id,
        ocr_result_id=ocr_result_id,
        accuracy_pct=accuracy_pct,
        details=details,
        db=db,
    )
    if result.status == OcrResultStatus.REVIEWED:
        db.transition_ocr_result_status(ocr_result_id, OcrResultStatus.SCORED)
    return snapshot



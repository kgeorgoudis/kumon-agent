"""Deterministic scoring service for manually entered worksheet answers."""

from __future__ import annotations

import hashlib
import json

from app.domain.models import ScoreResultSnapshot
from app.persistence.database import Database, default_db


class RescoreError(RuntimeError):
    """Base exception for rescoring failures."""


class RescoreNotReadyError(RescoreError):
    code = "ERR_REVIEW_NOT_COMPLETE"


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
        submission_id=submission_id,
        input_hash=input_hash,
        accuracy_pct=accuracy_pct,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.save_score_snapshot(snapshot)
    return snapshot

"""
SQLite persistence layer.

Design notes
------------
- Uses Python's built-in sqlite3 — zero extra dependencies.
- All domain objects are serialised to/from JSON via Pydantic.
- Append-only inserts are preferred; no silent updates.
- Constitutional Principle: Never lose the linkage between worksheet,
  submission, and decision.

Schema migrations are handled inline — each migration is idempotent
(uses CREATE TABLE IF NOT EXISTS and ALTER TABLE … IF NOT EXISTS patterns
where SQLite supports them).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import app.config as cfg
from app.domain.models import (
    ChildProfile,
    ManualAnswerEntry,
    ManualEntryMode,
    ManualSubmission,
    ManualSubmissionStatus,
    MicroSkillId,
    OcrField,
    OcrResult,
    OcrResultStatus,
    OcrValueSource,
    ScoreResultSnapshot,
    SubmissionStatus,
    WorksheetInstance,
    WorksheetSubmission,
    WorksheetType,
    can_transition_ocr_status,
)

# ── Schema DDL ────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS child_profiles (
    child_id            TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    age                 INTEGER NOT NULL,
    grade_level         INTEGER NOT NULL,
    locale              TEXT NOT NULL DEFAULT 'el-GR',
    language            TEXT NOT NULL DEFAULT 'el',
    preferred_sheet_length INTEGER NOT NULL DEFAULT 15,
    timing_enabled      INTEGER NOT NULL DEFAULT 0,
    review_mix_ratio    REAL    NOT NULL DEFAULT 0.2,
    notes               TEXT    NOT NULL DEFAULT '',
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS worksheet_instances (
    instance_id         TEXT PRIMARY KEY,
    child_id            TEXT,
    micro_skill_id      TEXT NOT NULL,
    worksheet_type      TEXT NOT NULL DEFAULT 'drill',
    exercises_json      TEXT NOT NULL,
    title_el            TEXT NOT NULL,
    instructions_el     TEXT NOT NULL,
    html_path           TEXT,
    answer_key_path     TEXT,
    seed                INTEGER,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (child_id) REFERENCES child_profiles(child_id)
);

CREATE INDEX IF NOT EXISTS idx_wi_child_id
    ON worksheet_instances (child_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wi_micro_skill
    ON worksheet_instances (micro_skill_id, created_at DESC);

CREATE TABLE IF NOT EXISTS worksheet_submissions (
    submission_id        TEXT PRIMARY KEY,
    instance_id          TEXT NOT NULL,
    child_id             TEXT,
    file_path            TEXT NOT NULL,
    mime_type            TEXT NOT NULL,
    file_hash            TEXT NOT NULL,
    uploaded_at          TEXT NOT NULL,
    status               TEXT NOT NULL,
    failure_reason       TEXT,
    FOREIGN KEY (instance_id) REFERENCES worksheet_instances(instance_id)
);

CREATE INDEX IF NOT EXISTS idx_ws_instance
    ON worksheet_submissions (instance_id, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS manual_submissions (
    submission_id        TEXT PRIMARY KEY,
    instance_id          TEXT NOT NULL,
    child_id             TEXT,
    status               TEXT NOT NULL,
    entry_mode           TEXT NOT NULL,
    duration_seconds     INTEGER,
    confirmed_at         TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    FOREIGN KEY (instance_id) REFERENCES worksheet_instances(instance_id)
);

CREATE INDEX IF NOT EXISTS idx_manual_submissions_instance
    ON manual_submissions (instance_id, created_at DESC);

CREATE TABLE IF NOT EXISTS manual_answer_entries (
    answer_entry_id      TEXT PRIMARY KEY,
    submission_id        TEXT NOT NULL,
    exercise_id          TEXT NOT NULL,
    slot_index           INTEGER NOT NULL,
    raw_value            TEXT NOT NULL,
    normalized_value     TEXT NOT NULL,
    is_valid             INTEGER NOT NULL,
    updated_at           TEXT NOT NULL,
    UNIQUE(submission_id, slot_index),
    FOREIGN KEY (submission_id) REFERENCES manual_submissions(submission_id)
);

CREATE INDEX IF NOT EXISTS idx_manual_answers_submission
    ON manual_answer_entries (submission_id, slot_index);

CREATE TABLE IF NOT EXISTS ocr_results (
    ocr_result_id        TEXT PRIMARY KEY,
    submission_id        TEXT NOT NULL,
    instance_id          TEXT NOT NULL,
    engine               TEXT NOT NULL,
    engine_version       TEXT NOT NULL,
    fallback_model       TEXT,
    confidence_threshold REAL NOT NULL DEFAULT 0.80,
    overall_confidence   REAL NOT NULL,
    status               TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    reviewed_at          TEXT,
    FOREIGN KEY (submission_id) REFERENCES worksheet_submissions(submission_id)
);

CREATE INDEX IF NOT EXISTS idx_ocr_submission
    ON ocr_results (submission_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ocr_fields (
    ocr_field_id         TEXT PRIMARY KEY,
    ocr_result_id        TEXT NOT NULL,
    exercise_id          TEXT NOT NULL,
    slot_index           INTEGER NOT NULL,
    raw_value            TEXT,
    confidence           REAL NOT NULL,
    needs_review         INTEGER NOT NULL,
    original_ocr_value   TEXT,
    corrected_value      TEXT,
    value_source         TEXT NOT NULL,
    bbox                 TEXT,
    updated_at           TEXT NOT NULL,
    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(ocr_result_id)
);

CREATE INDEX IF NOT EXISTS idx_ocr_fields_result
    ON ocr_fields (ocr_result_id, slot_index);

CREATE TABLE IF NOT EXISTS score_result_snapshots (
    score_result_id      TEXT PRIMARY KEY,
    instance_id          TEXT NOT NULL,
    ocr_result_id        TEXT,
    submission_id        TEXT,
    input_hash           TEXT NOT NULL,
    accuracy_pct         REAL NOT NULL,
    details_json         TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(ocr_result_id),
    FOREIGN KEY (submission_id) REFERENCES manual_submissions(submission_id)
);

CREATE INDEX IF NOT EXISTS idx_score_snapshots_ocr
    ON score_result_snapshots (ocr_result_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_score_snapshots_ocr_hash
    ON score_result_snapshots (ocr_result_id, input_hash)
    WHERE ocr_result_id IS NOT NULL;

"""


# ── Database class ────────────────────────────────────────────────────────────


class Database:
    """
    Thin wrapper around sqlite3 for the Kumon Agent persistence layer.

    Usage
    -----
    db = Database()                            # uses cfg.DB_PATH
    db = Database(Path("/tmp/test.db"))        # custom path (tests)

    with db.connect() as conn:                 # manual use
        rows = conn.execute("SELECT …").fetchall()

    # High-level helpers
    db.save_child_profile(profile)
    db.save_worksheet_instance(instance)
    profile = db.get_child_profile("default")
    sheets  = db.get_recent_worksheets("default", limit=5)
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or cfg.DB_PATH
        self._init_schema()

    # ── Connection helper ─────────────────────────────────────────────────────

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Schema initialisation ─────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA_SQL)
            _add_column_if_missing(conn, "ocr_results", "fallback_model", "TEXT")
            _add_column_if_missing(conn, "ocr_results", "confidence_threshold", "REAL NOT NULL DEFAULT 0.80")
            _add_column_if_missing(conn, "ocr_fields", "original_ocr_value", "TEXT")
            _add_column_if_missing(conn, "score_result_snapshots", "submission_id", "TEXT")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_score_snapshots_submission_hash
                ON score_result_snapshots (submission_id, input_hash)
                WHERE submission_id IS NOT NULL
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_score_snapshots_submission
                ON score_result_snapshots (submission_id, created_at DESC)
                """
            )

    # ── ChildProfile ──────────────────────────────────────────────────────────

    def save_child_profile(self, profile: ChildProfile) -> None:
        """Insert or replace a child profile."""
        now = _iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO child_profiles
                    (child_id, display_name, age, grade_level, locale, language,
                     preferred_sheet_length, timing_enabled, review_mix_ratio,
                     notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(child_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    age = excluded.age,
                    grade_level = excluded.grade_level,
                    locale = excluded.locale,
                    language = excluded.language,
                    preferred_sheet_length = excluded.preferred_sheet_length,
                    timing_enabled = excluded.timing_enabled,
                    review_mix_ratio = excluded.review_mix_ratio,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.child_id,
                    profile.display_name,
                    profile.age,
                    profile.grade_level,
                    profile.locale,
                    profile.language,
                    profile.preferred_sheet_length,
                    int(profile.timing_enabled),
                    profile.review_mix_ratio,
                    profile.notes,
                    _iso(profile.created_at),
                    now,
                ),
            )

    def get_child_profile(self, child_id: str) -> ChildProfile | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM child_profiles WHERE child_id = ?", (child_id,)
            ).fetchone()
        if row is None:
            return None
        return ChildProfile(
            child_id=row["child_id"],
            display_name=row["display_name"],
            age=row["age"],
            grade_level=row["grade_level"],
            locale=row["locale"],
            language=row["language"],
            preferred_sheet_length=row["preferred_sheet_length"],
            timing_enabled=bool(row["timing_enabled"]),
            review_mix_ratio=row["review_mix_ratio"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_child_profiles(self) -> list[ChildProfile]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM child_profiles ORDER BY display_name"
            ).fetchall()
        return [
            ChildProfile(
                child_id=r["child_id"],
                display_name=r["display_name"],
                age=r["age"],
                grade_level=r["grade_level"],
                locale=r["locale"],
                language=r["language"],
                preferred_sheet_length=r["preferred_sheet_length"],
                timing_enabled=bool(r["timing_enabled"]),
                review_mix_ratio=r["review_mix_ratio"],
                notes=r["notes"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in rows
        ]

    # ── WorksheetInstance ─────────────────────────────────────────────────────

    def save_worksheet_instance(self, instance: WorksheetInstance) -> None:
        exercises_json = json.dumps([ex.model_dump(mode="json") for ex in instance.exercises])
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO worksheet_instances
                    (instance_id, child_id, micro_skill_id, worksheet_type,
                     exercises_json, title_el, instructions_el,
                     html_path, answer_key_path, seed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance.instance_id,
                    instance.child_id,
                    instance.micro_skill_id.value,
                    instance.worksheet_type.value,
                    exercises_json,
                    instance.title_el,
                    instance.instructions_el,
                    instance.html_path,
                    instance.answer_key_path,
                    instance.seed,
                    _iso(instance.created_at),
                ),
            )

    def get_worksheet_instance(self, instance_id: str) -> WorksheetInstance | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM worksheet_instances WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_worksheet(row)

    def get_recent_worksheets(
        self,
        child_id: str | None = None,
        micro_skill_id: MicroSkillId | None = None,
        limit: int = 20,
    ) -> list[WorksheetInstance]:
        """Return worksheets in reverse-chronological order."""
        clauses: list[str] = []
        params: list[object] = []
        if child_id is not None:
            clauses.append("child_id = ?")
            params.append(child_id)
        if micro_skill_id is not None:
            clauses.append("micro_skill_id = ?")
            params.append(micro_skill_id.value)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM worksheet_instances {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [_row_to_worksheet(r) for r in rows]

    # ── OCR ingestion / review ────────────────────────────────────────────────

    def save_manual_submission(self, submission: ManualSubmission) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manual_submissions
                    (submission_id, instance_id, child_id, status, entry_mode,
                     duration_seconds, confirmed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission.submission_id,
                    submission.instance_id,
                    submission.child_id,
                    submission.status.value,
                    submission.entry_mode.value,
                    submission.duration_seconds,
                    _iso(submission.confirmed_at) if submission.confirmed_at else None,
                    _iso(submission.created_at),
                    _iso(submission.updated_at),
                ),
            )

    def get_manual_submission(self, submission_id: str) -> ManualSubmission | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM manual_submissions WHERE submission_id = ?",
                (submission_id,),
            ).fetchone()
        if row is None:
            return None
        return ManualSubmission(
            submission_id=row["submission_id"],
            instance_id=row["instance_id"],
            child_id=row["child_id"],
            status=ManualSubmissionStatus(row["status"]),
            entry_mode=ManualEntryMode(row["entry_mode"]),
            duration_seconds=row["duration_seconds"],
            confirmed_at=datetime.fromisoformat(row["confirmed_at"]) if row["confirmed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_confirmed_manual_submission_for_instance(self, instance_id: str) -> ManualSubmission | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM manual_submissions
                WHERE instance_id = ? AND status = ?
                ORDER BY confirmed_at DESC, created_at DESC
                LIMIT 1
                """,
                (instance_id, ManualSubmissionStatus.CONFIRMED.value),
            ).fetchone()
        if row is None:
            return None
        return self.get_manual_submission(row["submission_id"])

    def get_latest_draft_manual_submission(self, instance_id: str) -> ManualSubmission | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM manual_submissions
                WHERE instance_id = ? AND status = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                (instance_id, ManualSubmissionStatus.DRAFT.value),
            ).fetchone()
        if row is None:
            return None
        return self.get_manual_submission(row["submission_id"])

    def update_manual_submission_status(
        self,
        submission_id: str,
        status: ManualSubmissionStatus,
        duration_seconds: int | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        confirmed_at = _iso(now) if status == ManualSubmissionStatus.CONFIRMED else None
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE manual_submissions
                SET status = ?,
                    duration_seconds = COALESCE(?, duration_seconds),
                    confirmed_at = COALESCE(?, confirmed_at),
                    updated_at = ?
                WHERE submission_id = ?
                """,
                (
                    status.value,
                    duration_seconds,
                    confirmed_at,
                    _iso(now),
                    submission_id,
                ),
            )

    def save_manual_answer_entries(self, entries: list[ManualAnswerEntry]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO manual_answer_entries
                    (answer_entry_id, submission_id, exercise_id, slot_index,
                     raw_value, normalized_value, is_valid, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        entry.answer_entry_id,
                        entry.submission_id,
                        entry.exercise_id,
                        entry.slot_index,
                        entry.raw_value,
                        entry.normalized_value,
                        int(entry.is_valid),
                        _iso(entry.updated_at),
                    )
                    for entry in entries
                ],
            )

    def get_manual_answer_entries(self, submission_id: str) -> list[ManualAnswerEntry]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM manual_answer_entries
                WHERE submission_id = ?
                ORDER BY slot_index ASC
                """,
                (submission_id,),
            ).fetchall()
        return [
            ManualAnswerEntry(
                answer_entry_id=row["answer_entry_id"],
                submission_id=row["submission_id"],
                exercise_id=row["exercise_id"],
                slot_index=row["slot_index"],
                raw_value=row["raw_value"],
                normalized_value=row["normalized_value"],
                is_valid=bool(row["is_valid"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def upsert_manual_answer_entry(
        self,
        submission_id: str,
        exercise_id: str,
        slot_index: int,
        raw_value: str,
        normalized_value: str,
        is_valid: bool,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO manual_answer_entries
                    (answer_entry_id, submission_id, exercise_id, slot_index,
                     raw_value, normalized_value, is_valid, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(submission_id, slot_index) DO UPDATE SET
                    exercise_id = excluded.exercise_id,
                    raw_value = excluded.raw_value,
                    normalized_value = excluded.normalized_value,
                    is_valid = excluded.is_valid,
                    updated_at = excluded.updated_at
                """,
                (
                    f"{submission_id}:{slot_index}",
                    submission_id,
                    exercise_id,
                    slot_index,
                    raw_value,
                    normalized_value,
                    int(is_valid),
                    _iso(now),
                ),
            )

    def save_worksheet_submission(self, submission: WorksheetSubmission) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO worksheet_submissions
                    (submission_id, instance_id, child_id, file_path, mime_type,
                     file_hash, uploaded_at, status, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission.submission_id,
                    submission.instance_id,
                    submission.child_id,
                    submission.file_path,
                    submission.mime_type,
                    submission.file_hash,
                    _iso(submission.uploaded_at),
                    submission.status.value,
                    submission.failure_reason,
                ),
            )

    def get_submission(self, submission_id: str) -> WorksheetSubmission | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM worksheet_submissions WHERE submission_id = ?",
                (submission_id,),
            ).fetchone()
        if row is None:
            return None
        return WorksheetSubmission(
            submission_id=row["submission_id"],
            instance_id=row["instance_id"],
            child_id=row["child_id"],
            file_path=row["file_path"],
            mime_type=row["mime_type"],
            file_hash=row["file_hash"],
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            status=SubmissionStatus(row["status"]),
            failure_reason=row["failure_reason"],
        )

    def update_submission_status(
        self,
        submission_id: str,
        status: SubmissionStatus,
        failure_reason: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE worksheet_submissions
                SET status = ?, failure_reason = ?
                WHERE submission_id = ?
                """,
                (status.value, failure_reason, submission_id),
            )

    def save_ocr_result(self, result: OcrResult) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ocr_results
                    (ocr_result_id, submission_id, instance_id, engine,
                     engine_version, fallback_model, confidence_threshold,
                     overall_confidence, status, created_at, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.ocr_result_id,
                    result.submission_id,
                    result.instance_id,
                    result.engine,
                    result.engine_version,
                    result.fallback_model,
                    result.confidence_threshold,
                    result.overall_confidence,
                    result.status.value,
                    _iso(result.created_at),
                    _iso(result.reviewed_at) if result.reviewed_at else None,
                ),
            )

    def get_ocr_result(self, ocr_result_id: str) -> OcrResult | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM ocr_results WHERE ocr_result_id = ?",
                (ocr_result_id,),
            ).fetchone()
        if row is None:
            return None
        return OcrResult(
            ocr_result_id=row["ocr_result_id"],
            submission_id=row["submission_id"],
            instance_id=row["instance_id"],
            engine=row["engine"],
            engine_version=row["engine_version"],
            fallback_model=row["fallback_model"] if "fallback_model" in row.keys() else None,
            confidence_threshold=row["confidence_threshold"] if "confidence_threshold" in row.keys() else 0.80,
            overall_confidence=row["overall_confidence"],
            status=_parse_ocr_status(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            reviewed_at=datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None,
        )

    def save_ocr_fields(self, fields: list[OcrField]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO ocr_fields
                    (ocr_field_id, ocr_result_id, exercise_id, slot_index,
                     raw_value, confidence, needs_review, original_ocr_value, corrected_value,
                     value_source, bbox, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f.ocr_field_id,
                        f.ocr_result_id,
                        f.exercise_id,
                        f.slot_index,
                        f.raw_value,
                        f.confidence,
                        int(f.needs_review),
                        f.original_ocr_value,
                        f.corrected_value,
                        f.value_source.value,
                        f.bbox,
                        _iso(f.updated_at),
                    )
                    for f in fields
                ],
            )

    def get_ocr_fields(self, ocr_result_id: str) -> list[OcrField]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ocr_fields WHERE ocr_result_id = ? ORDER BY slot_index ASC",
                (ocr_result_id,),
            ).fetchall()
        return [
            OcrField(
                ocr_field_id=r["ocr_field_id"],
                ocr_result_id=r["ocr_result_id"],
                exercise_id=r["exercise_id"],
                slot_index=r["slot_index"],
                raw_value=r["raw_value"],
                confidence=r["confidence"],
                needs_review=bool(r["needs_review"]),
                original_ocr_value=r["original_ocr_value"] if "original_ocr_value" in r.keys() else None,
                corrected_value=r["corrected_value"],
                value_source=OcrValueSource(r["value_source"]),
                bbox=r["bbox"],
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in rows
        ]

    def update_ocr_field_correction(
        self,
        ocr_field_id: str,
        corrected_value: str,
        value_source: OcrValueSource = OcrValueSource.MANUAL,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE ocr_fields
                SET corrected_value = ?,
                    original_ocr_value = COALESCE(original_ocr_value, raw_value),
                    value_source = ?,
                    updated_at = ?
                WHERE ocr_field_id = ?
                """,
                (corrected_value, value_source.value, _iso(datetime.now(timezone.utc)), ocr_field_id),
            )

    def transition_ocr_result_status(
        self,
        ocr_result_id: str,
        target_status: OcrResultStatus,
    ) -> None:
        result = self.get_ocr_result(ocr_result_id)
        if result is None:
            return
        if not can_transition_ocr_status(result.status, target_status):
            raise ValueError(f"Invalid OCR status transition: {result.status.value} -> {target_status.value}")
        reviewed_at_value = _iso(datetime.now(timezone.utc)) if target_status == OcrResultStatus.REVIEWED else (
            _iso(result.reviewed_at) if result.reviewed_at else None
        )
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE ocr_results
                SET status = ?, reviewed_at = ?
                WHERE ocr_result_id = ?
                """,
                (target_status.value, reviewed_at_value, ocr_result_id),
            )

    def mark_ocr_result_reviewed(self, ocr_result_id: str) -> None:
        self.transition_ocr_result_status(ocr_result_id, OcrResultStatus.REVIEWED)

    def save_score_snapshot(self, snapshot: ScoreResultSnapshot) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO score_result_snapshots
                    (score_result_id, instance_id, ocr_result_id, submission_id,
                     input_hash, accuracy_pct, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.score_result_id,
                    snapshot.instance_id,
                    snapshot.ocr_result_id,
                    snapshot.submission_id,
                    snapshot.input_hash,
                    snapshot.accuracy_pct,
                    snapshot.details_json,
                    _iso(snapshot.created_at),
                ),
            )

    def get_score_snapshot_by_hash(
        self,
        ocr_result_id: str,
        input_hash: str,
    ) -> ScoreResultSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM score_result_snapshots
                WHERE ocr_result_id = ? AND input_hash = ?
                """,
                (ocr_result_id, input_hash),
            ).fetchone()
        if row is None:
            return None
        return ScoreResultSnapshot(
            score_result_id=row["score_result_id"],
            instance_id=row["instance_id"],
            ocr_result_id=row["ocr_result_id"],
            submission_id=row["submission_id"] if "submission_id" in row.keys() else None,
            input_hash=row["input_hash"],
            accuracy_pct=row["accuracy_pct"],
            details_json=row["details_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_score_snapshot_by_submission_hash(
        self,
        submission_id: str,
        input_hash: str,
    ) -> ScoreResultSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM score_result_snapshots
                WHERE submission_id = ? AND input_hash = ?
                """,
                (submission_id, input_hash),
            ).fetchone()
        if row is None:
            return None
        return ScoreResultSnapshot(
            score_result_id=row["score_result_id"],
            instance_id=row["instance_id"],
            ocr_result_id=row["ocr_result_id"],
            submission_id=row["submission_id"],
            input_hash=row["input_hash"],
            accuracy_pct=row["accuracy_pct"],
            details_json=row["details_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_score_snapshots(self, ocr_result_id: str) -> list[ScoreResultSnapshot]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM score_result_snapshots
                WHERE ocr_result_id = ?
                ORDER BY created_at DESC
                """,
                (ocr_result_id,),
            ).fetchall()
        return [
            ScoreResultSnapshot(
                score_result_id=r["score_result_id"],
                instance_id=r["instance_id"],
                ocr_result_id=r["ocr_result_id"],
                submission_id=r["submission_id"] if "submission_id" in r.keys() else None,
                input_hash=r["input_hash"],
                accuracy_pct=r["accuracy_pct"],
                details_json=r["details_json"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _parse_ocr_status(raw: str) -> OcrResultStatus:
    # Backward compatibility for rows persisted before lifecycle expansion.
    if raw == "pending_review":
        return OcrResultStatus.NEEDS_REVIEW
    if raw == "rejected":
        return OcrResultStatus.MISMATCHED
    return OcrResultStatus(raw)


def _row_to_worksheet(row: sqlite3.Row) -> WorksheetInstance:
    from app.domain.models import Exercise  # local import to avoid circular

    exercises = [Exercise(**ex) for ex in json.loads(row["exercises_json"])]
    return WorksheetInstance(
        instance_id=row["instance_id"],
        child_id=row["child_id"],
        micro_skill_id=MicroSkillId(row["micro_skill_id"]),
        worksheet_type=WorksheetType(row["worksheet_type"]),
        exercises=exercises,
        title_el=row["title_el"],
        instructions_el=row["instructions_el"],
        html_path=row["html_path"],
        answer_key_path=row["answer_key_path"],
        seed=row["seed"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ── Module-level default instance ─────────────────────────────────────────────
# Import and use `default_db` in service code and CLI.

default_db = Database()


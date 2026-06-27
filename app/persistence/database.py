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
from datetime import datetime, timedelta, timezone
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
    PendingWorksheetRow,
    ProgressWorksheetPoint,
    ProgressDecision,
    ScoreResultSnapshot,
    TutorStepStatus,
    TutorStepTrace,
    TutorTaskState,
    TutorTaskStatus,
    TutorTaskType,
    WorksheetInstance,
    WorksheetType,
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

CREATE TABLE IF NOT EXISTS progress_decisions (
    decision_id          TEXT PRIMARY KEY,
    child_id             TEXT NOT NULL,
    from_micro_skill_id  TEXT NOT NULL,
    next_micro_skill_id  TEXT NOT NULL,
    action               TEXT NOT NULL,
    reason               TEXT NOT NULL,
    reason_el            TEXT NOT NULL,
    accuracy_pct         REAL NOT NULL,
    parent_override      INTEGER NOT NULL DEFAULT 0,
    override_note        TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_progress_decisions_child_skill
    ON progress_decisions (child_id, from_micro_skill_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_runs (
    task_id                   TEXT PRIMARY KEY,
    task_type                 TEXT NOT NULL,
    child_id                  TEXT,
    prompt_version            TEXT NOT NULL,
    status                    TEXT NOT NULL,
    deterministic_context_json TEXT NOT NULL,
    model_context_json        TEXT NOT NULL,
    output_json               TEXT NOT NULL,
    error_code                TEXT,
    created_at                TEXT NOT NULL,
    updated_at                TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_child_time
    ON agent_runs (child_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runs_status_time
    ON agent_runs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runs_type_time
    ON agent_runs (task_type, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_step_runs (
    step_id                   TEXT PRIMARY KEY,
    task_id                   TEXT NOT NULL,
    step_name                 TEXT NOT NULL,
    status                    TEXT NOT NULL,
    input_snapshot_json       TEXT NOT NULL,
    output_snapshot_json      TEXT NOT NULL,
    error_code                TEXT,
    started_at                TEXT NOT NULL,
    finished_at               TEXT,
    FOREIGN KEY (task_id) REFERENCES agent_runs(task_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_step_runs_task_time
    ON agent_step_runs (task_id, started_at ASC);


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
            # Legacy migration: make ocr_result_id nullable in score snapshots.
            # OCR capability has been removed; this migration is kept to ensure
            # existing databases upgrade cleanly without errors.
            _migrate_score_snapshots_nullable_ocr(conn)
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
        # Keep optional fields in the serialized payload so extended exercise
        # schemas (e.g., ordering metadata) round-trip without loss.
        exercises_json = json.dumps(
            [ex.model_dump(mode="json", exclude_none=False) for ex in instance.exercises]
        )
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

    def list_pending_worksheets(
        self,
        child_id: str | None = None,
        limit: int = 20,
    ) -> list[PendingWorksheetRow]:
        """Return worksheets that do not yet have a confirmed manual submission."""
        clauses = [
            """
            NOT EXISTS (
                SELECT 1
                FROM manual_submissions msc
                WHERE msc.instance_id = wi.instance_id
                  AND msc.status = ?
            )
            """
        ]
        params: list[object] = [ManualSubmissionStatus.CONFIRMED.value]
        if child_id is not None:
            clauses.append("wi.child_id = ?")
            params.append(child_id)
        params.append(limit)

        where_sql = " AND ".join(clause.strip() for clause in clauses)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    wi.instance_id,
                    wi.child_id,
                    wi.title_el,
                    wi.exercises_json,
                    wi.created_at,
                    EXISTS (
                        SELECT 1
                        FROM manual_submissions msd
                        WHERE msd.instance_id = wi.instance_id
                          AND msd.status = ?
                    ) AS has_draft_submission,
                    (
                        SELECT msd.submission_id
                        FROM manual_submissions msd
                        WHERE msd.instance_id = wi.instance_id
                          AND msd.status = ?
                        ORDER BY msd.updated_at DESC, msd.created_at DESC
                        LIMIT 1
                    ) AS latest_draft_submission_id
                FROM worksheet_instances wi
                WHERE {where_sql}
                ORDER BY wi.created_at DESC
                LIMIT ?
                """,
                [
                    ManualSubmissionStatus.DRAFT.value,
                    ManualSubmissionStatus.DRAFT.value,
                    *params,
                ],
            ).fetchall()

        projections: list[PendingWorksheetRow] = []
        for row in rows:
            exercises = json.loads(row["exercises_json"])
            projections.append(
                PendingWorksheetRow(
                    instance_id=row["instance_id"],
                    child_id=row["child_id"],
                    title_el=row["title_el"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    exercise_count=len(exercises),
                    has_draft_submission=bool(row["has_draft_submission"]),
                    latest_draft_submission_id=row["latest_draft_submission_id"],
                )
            )
        return projections

    def list_progress_points(
        self,
        child_id: str,
        limit: int = 20,
    ) -> list[ProgressWorksheetPoint]:
        """Return confirmed scored worksheet points for progress summary reporting.

        Only manual submission snapshots (linked by submission_id) are counted.
        """
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    wi.instance_id,
                    wi.child_id,
                    wi.micro_skill_id,
                    wi.title_el,
                    ms.submission_id,
                    ms.confirmed_at,
                    (SELECT s.accuracy_pct FROM score_result_snapshots s
                     WHERE s.submission_id = ms.submission_id
                     ORDER BY s.created_at DESC LIMIT 1) AS accuracy_pct,
                    (SELECT s.details_json FROM score_result_snapshots s
                     WHERE s.submission_id = ms.submission_id
                     ORDER BY s.created_at DESC LIMIT 1) AS details_json
                FROM manual_submissions ms
                JOIN worksheet_instances wi
                    ON wi.instance_id = ms.instance_id
                WHERE ms.status = ?
                  AND wi.child_id = ?
                  AND ms.confirmed_at IS NOT NULL
                  AND (
                    SELECT COUNT(*) FROM score_result_snapshots s
                    WHERE s.submission_id = ms.submission_id
                  ) > 0
                ORDER BY ms.confirmed_at DESC
                LIMIT ?
                """,
                (ManualSubmissionStatus.CONFIRMED.value, child_id, limit),
            ).fetchall()

        points: list[ProgressWorksheetPoint] = []
        for row in rows:
            correct_count, total_count = _extract_score_counts(row["details_json"], row["accuracy_pct"])
            points.append(
                ProgressWorksheetPoint(
                    instance_id=row["instance_id"],
                    submission_id=row["submission_id"],
                    child_id=row["child_id"],
                    micro_skill_id=row["micro_skill_id"],
                    title_el=row["title_el"],
                    accuracy_pct=row["accuracy_pct"],
                    correct_count=correct_count,
                    total_count=total_count,
                    confirmed_at=datetime.fromisoformat(row["confirmed_at"]),
                )
            )
        return points

    # ── Manual submission ────────────────────────────────────────────────��────

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


    def save_score_snapshot(self, snapshot: ScoreResultSnapshot) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO score_result_snapshots
                    (score_result_id, instance_id, ocr_result_id, submission_id,
                     input_hash, accuracy_pct, details_json, created_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.score_result_id,
                    snapshot.instance_id,
                    snapshot.submission_id,
                    snapshot.input_hash,
                    snapshot.accuracy_pct,
                    snapshot.details_json,
                    _iso(snapshot.created_at),
                ),
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
            submission_id=row["submission_id"],
            input_hash=row["input_hash"],
            accuracy_pct=row["accuracy_pct"],
            details_json=row["details_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_latest_score_snapshot_for_submission(
        self,
        submission_id: str,
    ) -> ScoreResultSnapshot | None:
        """Return the most recent score snapshot for a confirmed manual submission."""
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM score_result_snapshots
                WHERE submission_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (submission_id,),
            ).fetchone()
        if row is None:
            return None
        return ScoreResultSnapshot(
            score_result_id=row["score_result_id"],
            instance_id=row["instance_id"],
            submission_id=row["submission_id"],
            input_hash=row["input_hash"],
            accuracy_pct=row["accuracy_pct"],
            details_json=row["details_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


    def list_unscored_confirmed_submissions(
        self, child_id: str | None = None
    ) -> list[ManualSubmission]:
        """Return confirmed manual submissions that have no score snapshot.

        Used by the backfill command to recover data after the NOT NULL migration.
        """
        clauses = ["ms.status = ?"]
        params: list[object] = [ManualSubmissionStatus.CONFIRMED.value]
        if child_id is not None:
            clauses.append("wi.child_id = ?")
            params.append(child_id)
        where = " AND ".join(clauses)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT ms.*
                FROM manual_submissions ms
                JOIN worksheet_instances wi ON wi.instance_id = ms.instance_id
                WHERE {where}
                  AND NOT EXISTS (
                    SELECT 1 FROM score_result_snapshots s
                    WHERE s.submission_id = ms.submission_id
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM score_result_snapshots s
                    WHERE s.instance_id = ms.instance_id AND s.submission_id IS NULL
                  )
                ORDER BY ms.confirmed_at ASC
                """,
                params,
            ).fetchall()
        return [
            ManualSubmission(
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
            for row in rows
        ]

    def save_progress_decision(self, decision: ProgressDecision) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO progress_decisions
                    (decision_id, child_id, from_micro_skill_id, next_micro_skill_id,
                     action, reason, reason_el, accuracy_pct,
                     parent_override, override_note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.child_id,
                    decision.from_micro_skill_id.value,
                    decision.next_micro_skill_id.value,
                    decision.action,
                    decision.reason,
                    decision.reason_el,
                    decision.accuracy_pct,
                    int(decision.parent_override),
                    decision.override_note,
                    _iso(decision.created_at),
                ),
            )

    def get_latest_progress_decision(
        self,
        child_id: str,
        micro_skill_id: MicroSkillId,
    ) -> ProgressDecision | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM progress_decisions
                WHERE child_id = ? AND from_micro_skill_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (child_id, micro_skill_id.value),
            ).fetchone()
        if row is None:
            return None

        return ProgressDecision(
            decision_id=row["decision_id"],
            child_id=row["child_id"],
            from_micro_skill_id=MicroSkillId(row["from_micro_skill_id"]),
            next_micro_skill_id=MicroSkillId(row["next_micro_skill_id"]),
            action=row["action"],
            reason=row["reason"],
            reason_el=row["reason_el"],
            accuracy_pct=row["accuracy_pct"],
            created_at=datetime.fromisoformat(row["created_at"]),
            parent_override=bool(row["parent_override"]),
            override_note=row["override_note"],
        )

    def save_agent_run(self, run: TutorTaskState) -> None:
        """Insert or update one tutor task run record."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs
                    (task_id, task_type, child_id, prompt_version, status,
                     deterministic_context_json, model_context_json, output_json,
                     error_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status = excluded.status,
                    deterministic_context_json = excluded.deterministic_context_json,
                    model_context_json = excluded.model_context_json,
                    output_json = excluded.output_json,
                    error_code = excluded.error_code,
                    updated_at = excluded.updated_at
                """,
                (
                    run.task_id,
                    run.task_type.value,
                    run.child_id,
                    run.prompt_version,
                    run.status.value,
                    json.dumps(run.deterministic_context, ensure_ascii=False),
                    json.dumps(run.model_context, ensure_ascii=False),
                    json.dumps(run.output, ensure_ascii=False),
                    run.error_code,
                    _iso(run.created_at),
                    _iso(run.updated_at),
                ),
            )

    def get_agent_run(self, task_id: str) -> TutorTaskState | None:
        """Return one tutor task run by id."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_runs WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return TutorTaskState(
            task_id=row["task_id"],
            task_type=TutorTaskType(row["task_type"]),
            child_id=row["child_id"],
            prompt_version=row["prompt_version"],
            status=TutorTaskStatus(row["status"]),
            deterministic_context=json.loads(row["deterministic_context_json"]),
            model_context=json.loads(row["model_context_json"]),
            output=json.loads(row["output_json"]),
            error_code=row["error_code"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def save_agent_step_run(self, step: TutorStepTrace) -> None:
        """Insert or update one tutor step trace row."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_step_runs
                    (step_id, task_id, step_name, status,
                     input_snapshot_json, output_snapshot_json, error_code,
                     started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(step_id) DO UPDATE SET
                    status = excluded.status,
                    output_snapshot_json = excluded.output_snapshot_json,
                    error_code = excluded.error_code,
                    finished_at = excluded.finished_at
                """,
                (
                    step.step_id,
                    step.task_id,
                    step.step_name,
                    step.status.value,
                    json.dumps(step.input_snapshot, ensure_ascii=False),
                    json.dumps(step.output_snapshot, ensure_ascii=False),
                    step.error_code,
                    _iso(step.started_at),
                    _iso(step.finished_at) if step.finished_at else None,
                ),
            )

    def list_agent_runs(
        self,
        *,
        status: TutorTaskStatus | None = None,
        task_type: TutorTaskType | None = None,
        hours: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        """Return run summaries with optional filtering by status/type/time window."""
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if task_type is not None:
            clauses.append("task_type = ?")
            params.append(task_type.value)
        if hours is not None:
            clauses.append("created_at >= ?")
            params.append(_iso(datetime.now(timezone.utc) - timedelta(hours=hours)))

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT task_id, task_type, status, prompt_version, error_code, created_at, updated_at
                FROM agent_runs{where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()

        return [
            {
                "task_id": row["task_id"],
                "task_type": row["task_type"],
                "status": row["status"],
                "prompt_version": row["prompt_version"],
                "error_code": row["error_code"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


    def list_agent_step_runs(self, task_id: str) -> list[TutorStepTrace]:
        """Return all step traces for one task in chronological order."""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM agent_step_runs
                WHERE task_id = ?
                ORDER BY started_at ASC
                """,
                (task_id,),
            ).fetchall()
        traces: list[TutorStepTrace] = []
        for row in rows:
            traces.append(
                TutorStepTrace(
                    step_id=row["step_id"],
                    task_id=row["task_id"],
                    step_name=row["step_name"],
                    status=TutorStepStatus(row["status"]),
                    input_snapshot=json.loads(row["input_snapshot_json"]),
                    output_snapshot=json.loads(row["output_snapshot_json"]),
                    error_code=row["error_code"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    finished_at=(
                        datetime.fromisoformat(row["finished_at"])
                        if row["finished_at"]
                        else None
                    ),
                )
            )
        return traces


# ── Helpers ───────────────────────────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _migrate_score_snapshots_nullable_ocr(conn: sqlite3.Connection) -> None:
    """One-time migration: make score_result_snapshots.ocr_result_id nullable.

    The original schema defined ocr_result_id as NOT NULL. Manual submission
    snapshots legitimately have ocr_result_id=NULL, so INSERT OR IGNORE was
    silently swallowing every such insert due to the NOT NULL violation.
    This migration recreates the table with the correct nullable column and
    rebuilds all indexes.
    """
    col_info = {
        row[1]: row[3]  # name → notnull flag
        for row in conn.execute("PRAGMA table_info(score_result_snapshots)").fetchall()
    }
    if not col_info.get("ocr_result_id", 0):
        return  # already nullable — nothing to do

    conn.executescript(
        """
        BEGIN;
        CREATE TABLE score_result_snapshots_v2 (
            score_result_id      TEXT PRIMARY KEY,
            instance_id          TEXT NOT NULL,
            ocr_result_id        TEXT,
            submission_id        TEXT,
            input_hash           TEXT NOT NULL,
            accuracy_pct         REAL NOT NULL,
            details_json         TEXT NOT NULL,
            created_at           TEXT NOT NULL
        );
        INSERT OR IGNORE INTO score_result_snapshots_v2
            SELECT score_result_id, instance_id, ocr_result_id, submission_id,
                   input_hash, accuracy_pct, details_json, created_at
            FROM score_result_snapshots;
        DROP TABLE score_result_snapshots;
        ALTER TABLE score_result_snapshots_v2 RENAME TO score_result_snapshots;
        CREATE INDEX IF NOT EXISTS idx_score_snapshots_ocr
            ON score_result_snapshots (ocr_result_id, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_score_snapshots_ocr_hash
            ON score_result_snapshots (ocr_result_id, input_hash)
            WHERE ocr_result_id IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_score_snapshots_submission_hash
            ON score_result_snapshots (submission_id, input_hash)
            WHERE submission_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_score_snapshots_submission
            ON score_result_snapshots (submission_id, created_at DESC);
        COMMIT;
        """
    )




def _extract_score_counts(details_json: str, accuracy_pct: float) -> tuple[int, int]:
    """Extract deterministic score counts from snapshot details payload."""
    try:
        details = json.loads(details_json)
    except json.JSONDecodeError:
        return 0, 0

    total = details.get("total_count")
    correct = details.get("correct_count")
    if isinstance(total, int) and isinstance(correct, int) and total >= 0 and correct >= 0:
        return correct, total

    entries = details.get("entries") if isinstance(details, dict) else None
    if isinstance(entries, list):
        total = len(entries)
        correct = round(total * (accuracy_pct / 100.0))
        return max(correct, 0), max(total, 0)

    return 0, 0


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


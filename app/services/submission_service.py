"""Manual worksheet submission service.

Covers:
- deterministic answer normalization/validation helpers  (Phase 2)
- bulk parsing + duration parsing helpers               (Phase 2)
- submission init / duplicate guard                     (US1)
- confirm-and-score flow                                (US1)
- review summary + targeted slot correction             (US2)
- draft resume / cancellation                           (US2)
- optional timing persistence                           (US3)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.models import (
    ManualAnswerEntry,
    ManualEntryMode,
    ManualSubmission,
    ManualSubmissionStatus,
    PendingWorksheetRow,
)
from app.persistence.database import Database, default_db


# ── Errors ────────────────────────────────────────────────────────────────────


class SubmissionServiceError(RuntimeError):
    """Base exception for manual submission workflow errors."""


class InvalidAnswerFormatError(SubmissionServiceError):
    code = "ERR_INVALID_ANSWER_FORMAT"


class AnswerCountMismatchError(SubmissionServiceError):
    code = "ERR_ANSWER_COUNT_MISMATCH"


class InvalidDurationFormatError(SubmissionServiceError):
    code = "ERR_INVALID_DURATION_FORMAT"


class WorksheetNotFoundError(SubmissionServiceError):
    code = "ERR_WORKSHEET_NOT_FOUND"


class SubmissionAlreadyConfirmedError(SubmissionServiceError):
    code = "ERR_SUBMISSION_ALREADY_CONFIRMED"


class DraftNotFoundError(SubmissionServiceError):
    code = "ERR_DRAFT_NOT_FOUND"


class SubmissionNotFoundError(SubmissionServiceError):
    code = "ERR_SUBMISSION_NOT_FOUND"


class SubmissionNotDraftError(SubmissionServiceError):
    code = "ERR_SUBMISSION_NOT_DRAFT"


# ── Value objects ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NormalizedAnswer:
    raw_value: str
    normalized_value: str
    is_valid: bool


@dataclass(frozen=True)
class AnswerReviewRow:
    slot_index: int
    exercise_id: str
    problem_text: str
    raw_value: str
    normalized_value: str
    is_valid: bool


@dataclass(frozen=True)
class SubmitOutcome:
    submission_id: str
    instance_id: str
    score_result_id: str
    input_hash: str
    accuracy_pct: float
    correct_count: int
    total_count: int
    duration_seconds: int | None
    details_json: str


# ── Answer helpers ────────────────────────────────────────────────────────────


def normalize_answer(raw_value: str) -> NormalizedAnswer:
    """Normalize a manually entered numeric answer deterministically.

    Rules:
    - Trim whitespace.
    - Convert decimal comma to decimal dot.
    - Validate as int/decimal/fraction form.
    """
    value = raw_value.strip().replace(",", ".")
    if value == "":
        return NormalizedAnswer(raw_value=raw_value, normalized_value="", is_valid=False)

    # Accepted forms: 12, -12, 3.5, -3.5, 3/4, -3/4
    is_valid = bool(re.fullmatch(r"-?(?:\d+(?:\.\d+)?|\d+/\d+)", value))
    return NormalizedAnswer(raw_value=raw_value, normalized_value=value, is_valid=is_valid)


def validate_answer(raw_value: str) -> str:
    """Return normalized answer string or raise invalid format error."""
    normalized = normalize_answer(raw_value)
    if not normalized.is_valid:
        raise InvalidAnswerFormatError(f"Invalid answer format: {raw_value!r}")
    return normalized.normalized_value


def parse_bulk_answers(raw_answers: str, expected_count: int) -> list[str]:
    """Parse comma/whitespace separated answers and validate expected size."""
    if "," in raw_answers:
        parts = [part.strip() for part in raw_answers.split(",")]
    else:
        parts = [part.strip() for part in raw_answers.split()]

    answers = [part for part in parts if part != ""]
    if len(answers) != expected_count:
        raise AnswerCountMismatchError(
            f"Expected {expected_count} answers but received {len(answers)}"
        )
    return answers


def parse_duration_to_seconds(raw_duration: str) -> int:
    """Parse duration in SS, MM:SS, or Xm format into integer seconds."""
    value = raw_duration.strip().lower()

    if re.fullmatch(r"\d+", value):
        return int(value)

    mm_ss = re.fullmatch(r"(\d+):(\d{1,2})", value)
    if mm_ss:
        minutes = int(mm_ss.group(1))
        seconds = int(mm_ss.group(2))
        if seconds >= 60:
            raise InvalidDurationFormatError(f"Invalid duration format: {raw_duration!r}")
        return minutes * 60 + seconds

    minutes_only = re.fullmatch(r"(\d+)m", value)
    if minutes_only:
        return int(minutes_only.group(1)) * 60

    raise InvalidDurationFormatError(f"Invalid duration format: {raw_duration!r}")


def _score_answers(normalized_values: list[str], correct_answers: list[str | float | int]) -> tuple[int, int]:
    """Compare normalized answer strings against correct answers.

    Returns (correct_count, total_count). Comparison is numeric-aware:
    tries float equality first, then string equality.
    """
    correct = 0
    for submitted, expected in zip(normalized_values, correct_answers):
        expected_str = str(expected).strip()
        if submitted.strip() == expected_str:
            correct += 1
            continue
        try:
            if abs(float(submitted.strip()) - float(expected_str)) < 1e-9:
                correct += 1
        except (ValueError, ZeroDivisionError):
            pass
    return correct, len(correct_answers)


# ── Submission workflow ───────────────────────────────────────────────────────


def start_submission(
    instance_id: str,
    entry_mode: ManualEntryMode = ManualEntryMode.SEQUENTIAL,
    db: Database = default_db,
) -> ManualSubmission:
    """Validate worksheet exists and no confirmed submission yet, then create a draft."""
    worksheet = db.get_worksheet_instance(instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {instance_id}")

    existing_confirmed = db.get_confirmed_manual_submission_for_instance(instance_id)
    if existing_confirmed is not None:
        raise SubmissionAlreadyConfirmedError(
            f"A confirmed submission already exists for worksheet {instance_id}"
        )

    submission = ManualSubmission(
        instance_id=instance_id,
        child_id=worksheet.child_id,
        entry_mode=entry_mode,
    )
    db.save_manual_submission(submission)
    return submission


def resume_draft(instance_id: str, db: Database = default_db) -> ManualSubmission:
    """Return the latest draft for the given worksheet or raise if not found."""
    draft = db.get_latest_draft_manual_submission(instance_id)
    if draft is None:
        raise DraftNotFoundError(f"No draft submission found for worksheet {instance_id}")
    return draft


def set_answers_on_draft(
    submission_id: str,
    raw_answers: list[str],
    db: Database = default_db,
) -> list[ManualAnswerEntry]:
    """Persist normalized answers into a draft submission, replacing any existing entries.

    Returns the list of ManualAnswerEntry objects written.
    Raises SubmissionNotDraftError if submission is not in draft state.
    """
    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
    if submission.status != ManualSubmissionStatus.DRAFT:
        raise SubmissionNotDraftError(f"Cannot update answers on a {submission.status.value} submission")

    worksheet = db.get_worksheet_instance(submission.instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {submission.instance_id}")

    entries: list[ManualAnswerEntry] = []
    for idx, (raw, exercise) in enumerate(zip(raw_answers, worksheet.exercises)):
        norm = normalize_answer(raw)
        db.upsert_manual_answer_entry(
            submission_id=submission_id,
            exercise_id=exercise.exercise_id,
            slot_index=idx,
            raw_value=raw,
            normalized_value=norm.normalized_value,
            is_valid=norm.is_valid,
        )
        entries.append(
            ManualAnswerEntry(
                submission_id=submission_id,
                exercise_id=exercise.exercise_id,
                slot_index=idx,
                raw_value=raw,
                normalized_value=norm.normalized_value,
                is_valid=norm.is_valid,
            )
        )
    return entries


def update_single_answer(
    submission_id: str,
    slot_index: int,
    raw_value: str,
    db: Database = default_db,
) -> ManualAnswerEntry:
    """Replace one answer slot in a draft submission.

    Used by the review correction loop (US2).
    """
    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
    if submission.status != ManualSubmissionStatus.DRAFT:
        raise SubmissionNotDraftError(f"Cannot update answers on a {submission.status.value} submission")

    worksheet = db.get_worksheet_instance(submission.instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {submission.instance_id}")
    if slot_index < 0 or slot_index >= len(worksheet.exercises):
        raise InvalidAnswerFormatError(
            f"Slot index {slot_index} out of range for worksheet with {len(worksheet.exercises)} exercises"
        )

    exercise = worksheet.exercises[slot_index]
    norm = normalize_answer(raw_value)
    db.upsert_manual_answer_entry(
        submission_id=submission_id,
        exercise_id=exercise.exercise_id,
        slot_index=slot_index,
        raw_value=raw_value,
        normalized_value=norm.normalized_value,
        is_valid=norm.is_valid,
    )
    return ManualAnswerEntry(
        submission_id=submission_id,
        exercise_id=exercise.exercise_id,
        slot_index=slot_index,
        raw_value=raw_value,
        normalized_value=norm.normalized_value,
        is_valid=norm.is_valid,
    )


def get_review_summary(
    submission_id: str,
    db: Database = default_db,
) -> list[AnswerReviewRow]:
    """Return structured review rows pairing each slot with its entered answer."""
    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")

    worksheet = db.get_worksheet_instance(submission.instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {submission.instance_id}")

    entries = {e.slot_index: e for e in db.get_manual_answer_entries(submission_id)}
    rows: list[AnswerReviewRow] = []
    for idx, exercise in enumerate(worksheet.exercises):
        entry = entries.get(idx)
        rows.append(
            AnswerReviewRow(
                slot_index=idx,
                exercise_id=exercise.exercise_id,
                problem_text=exercise.problem_text,
                raw_value=entry.raw_value if entry else "",
                normalized_value=entry.normalized_value if entry else "",
                is_valid=entry.is_valid if entry else False,
            )
        )
    return rows


def cancel_submission(submission_id: str, db: Database = default_db) -> None:
    """Mark a draft submission as cancelled."""
    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
    if submission.status != ManualSubmissionStatus.DRAFT:
        return  # idempotent for non-draft
    db.update_manual_submission_status(submission_id, ManualSubmissionStatus.CANCELLED)


def list_pending_worksheets(
    child_id: str | None = None,
    limit: int = 20,
    db: Database = default_db,
) -> list[PendingWorksheetRow]:
    """Return worksheets that remain submittable (no confirmed submission yet)."""
    return db.list_pending_worksheets(child_id=child_id, limit=limit)


def confirm_and_score(
    submission_id: str,
    duration_seconds: int | None = None,
    db: Database = default_db,
) -> SubmitOutcome:
    """Confirm a draft, run deterministic scoring, and persist the score snapshot.

    This is the core transition: draft -> confirmed + ScoreResultSnapshot created.
    """
    from app.services.scoring_service import (
        build_manual_submission_input_hash,
    )

    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
    if submission.status != ManualSubmissionStatus.DRAFT:
        raise SubmissionNotDraftError(
            f"Cannot confirm a {submission.status.value} submission"
        )

    # Verify no duplicate confirmed submission (race condition guard)
    existing = db.get_confirmed_manual_submission_for_instance(submission.instance_id)
    if existing is not None and existing.submission_id != submission_id:
        raise SubmissionAlreadyConfirmedError(
            f"A confirmed submission already exists for worksheet {submission.instance_id}"
        )

    worksheet = db.get_worksheet_instance(submission.instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {submission.instance_id}")

    entries = db.get_manual_answer_entries(submission_id)
    entry_map = {e.slot_index: e for e in entries}

    # Build normalized answer list aligned to exercise order
    normalized_values: list[str] = []
    entry_dicts: list[dict] = []
    for idx, exercise in enumerate(worksheet.exercises):
        entry = entry_map.get(idx)
        norm_val = entry.normalized_value if entry else ""
        raw_val = entry.raw_value if entry else ""
        normalized_values.append(norm_val)
        entry_dicts.append(
            {
                "exercise_id": exercise.exercise_id,
                "slot_index": idx,
                "raw_value": raw_val,
                "normalized_value": norm_val,
                "is_valid": entry.is_valid if entry else False,
                "problem_text": exercise.problem_text,
                "correct_answer": str(exercise.answer),
            }
        )

    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    correct_count, total_count = _score_answers(normalized_values, correct_answers)
    accuracy_pct = (correct_count / total_count * 100.0) if total_count else 0.0

    details = {
        "entries": [
            {k: v for k, v in e.items() if k != "problem_text"}
            for e in entry_dicts
        ],
        "correct_count": correct_count,
        "total_count": total_count,
        "mode": "manual_deterministic",
    }

    input_hash = build_manual_submission_input_hash(
        submission.instance_id,
        submission_id,
        details["entries"],
    )

    # Check idempotency — same input already scored
    existing_snap = db.get_score_snapshot_by_submission_hash(submission_id, input_hash)
    if existing_snap is None:
        from app.domain.models import ScoreResultSnapshot
        snapshot = ScoreResultSnapshot(
            instance_id=submission.instance_id,
            submission_id=submission_id,
            input_hash=input_hash,
            accuracy_pct=accuracy_pct,
            details_json=json.dumps(details, ensure_ascii=False),
        )
        db.save_score_snapshot(snapshot)
    else:
        snapshot = existing_snap

    # Confirm submission + persist timing
    db.update_manual_submission_status(
        submission_id,
        ManualSubmissionStatus.CONFIRMED,
        duration_seconds=duration_seconds,
    )

    return SubmitOutcome(
        submission_id=submission_id,
        instance_id=submission.instance_id,
        score_result_id=snapshot.score_result_id,
        input_hash=input_hash,
        accuracy_pct=accuracy_pct,
        correct_count=correct_count,
        total_count=total_count,
        duration_seconds=duration_seconds,
        details_json=snapshot.details_json,
    )


def backfill_submission_snapshot(
    submission_id: str,
    db: Database = default_db,
) -> SubmitOutcome:
    """Re-score a confirmed submission that is missing a score snapshot.

    Used as a recovery tool after the NOT NULL migration that prevented snapshots
    from being persisted. Unlike confirm_and_score, this operates on CONFIRMED
    submissions without changing their status.
    """
    from app.services.scoring_service import build_manual_submission_input_hash

    submission = db.get_manual_submission(submission_id)
    if submission is None:
        raise SubmissionNotFoundError(f"Submission not found: {submission_id}")
    if submission.status != ManualSubmissionStatus.CONFIRMED:
        raise SubmissionNotDraftError(
            f"backfill_submission_snapshot requires a confirmed submission, got: {submission.status.value}"
        )

    worksheet = db.get_worksheet_instance(submission.instance_id)
    if worksheet is None:
        raise WorksheetNotFoundError(f"Worksheet not found: {submission.instance_id}")

    entries = db.get_manual_answer_entries(submission_id)
    entry_map = {e.slot_index: e for e in entries}

    normalized_values: list[str] = []
    entry_dicts: list[dict] = []
    for idx, exercise in enumerate(worksheet.exercises):
        entry = entry_map.get(idx)
        norm_val = entry.normalized_value if entry else ""
        raw_val = entry.raw_value if entry else ""
        normalized_values.append(norm_val)
        entry_dicts.append(
            {
                "exercise_id": exercise.exercise_id,
                "slot_index": idx,
                "raw_value": raw_val,
                "normalized_value": norm_val,
                "is_valid": entry.is_valid if entry else False,
                "correct_answer": str(exercise.answer),
            }
        )

    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    correct_count, total_count = _score_answers(normalized_values, correct_answers)
    accuracy_pct = (correct_count / total_count * 100.0) if total_count else 0.0

    details = {
        "entries": entry_dicts,
        "correct_count": correct_count,
        "total_count": total_count,
        "mode": "manual_deterministic",
    }

    input_hash = build_manual_submission_input_hash(
        submission.instance_id,
        submission_id,
        entry_dicts,
    )

    existing_snap = db.get_score_snapshot_by_submission_hash(submission_id, input_hash)
    if existing_snap is None:
        from app.domain.models import ScoreResultSnapshot
        snapshot = ScoreResultSnapshot(
            instance_id=submission.instance_id,
            submission_id=submission_id,
            input_hash=input_hash,
            accuracy_pct=accuracy_pct,
            details_json=json.dumps(details, ensure_ascii=False),
        )
        db.save_score_snapshot(snapshot)
    else:
        snapshot = existing_snap

    return SubmitOutcome(
        submission_id=submission_id,
        instance_id=submission.instance_id,
        score_result_id=snapshot.score_result_id,
        input_hash=input_hash,
        accuracy_pct=accuracy_pct,
        correct_count=correct_count,
        total_count=total_count,
        duration_seconds=submission.duration_seconds,
        details_json=snapshot.details_json,
    )



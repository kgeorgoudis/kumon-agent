from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.models import (
    ManualAnswerEntry,
    ManualEntryMode,
    ManualSubmission,
    ManualSubmissionStatus,
    MicroSkillId,
)
from app.persistence.database import Database
from app.services.scoring_service import build_manual_submission_input_hash, persist_manual_submission_snapshot
from app.services.submission_service import (
    AnswerCountMismatchError,
    DraftNotFoundError,
    InvalidAnswerFormatError,
    InvalidDurationFormatError,
    SubmissionAlreadyConfirmedError,
    SubmissionNotDraftError,
    cancel_submission,
    confirm_and_score,
    get_review_summary,
    normalize_answer,
    parse_bulk_answers,
    parse_duration_to_seconds,
    resume_draft,
    set_answers_on_draft,
    start_submission,
    update_single_answer,
    validate_answer,
    WorksheetNotFoundError,
)
from app.services.worksheet_generator import generate_worksheet
import app.config as cfg


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "manual_submission.db")


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def worksheet(db: Database, tmp_output):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=99)
    db.save_worksheet_instance(ws)
    return ws


@pytest.fixture()
def ordering_worksheet(db: Database, tmp_output):
    ws = generate_worksheet(MicroSkillId.ORDERING_NUMBERS, count=3, seed=31)
    db.save_worksheet_instance(ws)
    return ws


# ── Phase 2 foundational helpers ──────────────────────────────────────────────

def test_normalize_answer_accepts_decimal_comma_and_fraction():
    normalized_decimal = normalize_answer(" 3,5 ")
    assert normalized_decimal.normalized_value == "3.5"
    assert normalized_decimal.is_valid is True

    normalized_fraction = normalize_answer("3/4")
    assert normalized_fraction.normalized_value == "3/4"
    assert normalized_fraction.is_valid is True


def test_validate_answer_rejects_invalid_input():
    with pytest.raises(InvalidAnswerFormatError):
        validate_answer("1o")


def test_parse_bulk_answers_validates_count():
    parsed = parse_bulk_answers("1, 2, 3", expected_count=3)
    assert parsed == ["1", "2", "3"]

    with pytest.raises(AnswerCountMismatchError):
        parse_bulk_answers("1,2", expected_count=3)


def test_parse_bulk_answers_accepts_semicolon_delimiter():
    parsed = parse_bulk_answers("1 2 3; 4 5 6; 7 8 9", expected_count=3)
    assert parsed == ["1 2 3", "4 5 6", "7 8 9"]


def test_parse_duration_to_seconds_formats():
    assert parse_duration_to_seconds("75") == 75
    assert parse_duration_to_seconds("12:34") == 754
    assert parse_duration_to_seconds("9m") == 540

    with pytest.raises(InvalidDurationFormatError):
        parse_duration_to_seconds("12:67")


def test_manual_submission_db_crud_and_draft_lookup(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=5)
    db.save_worksheet_instance(ws)

    submission = ManualSubmission(
        instance_id=ws.instance_id,
        child_id=ws.child_id,
        entry_mode=ManualEntryMode.BULK,
    )
    db.save_manual_submission(submission)

    fetched = db.get_manual_submission(submission.submission_id)
    assert fetched is not None
    assert fetched.status == ManualSubmissionStatus.DRAFT

    latest_draft = db.get_latest_draft_manual_submission(ws.instance_id)
    assert latest_draft is not None
    assert latest_draft.submission_id == submission.submission_id

    db.update_manual_submission_status(submission.submission_id, ManualSubmissionStatus.CONFIRMED, duration_seconds=90)
    confirmed = db.get_confirmed_manual_submission_for_instance(ws.instance_id)
    assert confirmed is not None
    assert confirmed.duration_seconds == 90


def test_manual_answer_entries_upsert_and_retrieve(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=2)
    db.save_worksheet_instance(ws)

    submission = ManualSubmission(instance_id=ws.instance_id)
    db.save_manual_submission(submission)

    entries = [
        ManualAnswerEntry(
            submission_id=submission.submission_id,
            exercise_id=ws.exercises[0].exercise_id,
            slot_index=0,
            raw_value="5",
            normalized_value="5",
            is_valid=True,
        ),
        ManualAnswerEntry(
            submission_id=submission.submission_id,
            exercise_id=ws.exercises[1].exercise_id,
            slot_index=1,
            raw_value="6",
            normalized_value="6",
            is_valid=True,
        ),
    ]
    db.save_manual_answer_entries(entries)

    db.upsert_manual_answer_entry(
        submission_id=submission.submission_id,
        exercise_id=ws.exercises[1].exercise_id,
        slot_index=1,
        raw_value="7",
        normalized_value="7",
        is_valid=True,
    )

    fetched = db.get_manual_answer_entries(submission.submission_id)
    assert [e.slot_index for e in fetched] == [0, 1]
    assert fetched[1].normalized_value == "7"


def test_manual_submission_hash_is_deterministic():
    entries_a = [
        {"exercise_id": "b", "slot_index": 1, "raw_value": "2", "normalized_value": "2", "is_valid": True},
        {"exercise_id": "a", "slot_index": 0, "raw_value": "1", "normalized_value": "1", "is_valid": True},
    ]
    entries_b = list(reversed(entries_a))

    h1 = build_manual_submission_input_hash("instance", "submission", entries_a)
    h2 = build_manual_submission_input_hash("instance", "submission", entries_b)
    assert h1 == h2


def test_manual_snapshot_persistence_is_idempotent(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=2, seed=3)
    db.save_worksheet_instance(ws)
    submission = ManualSubmission(instance_id=ws.instance_id)
    db.save_manual_submission(submission)

    details = {
        "entries": [
            {
                "exercise_id": ws.exercises[0].exercise_id,
                "slot_index": 0,
                "raw_value": "4",
                "normalized_value": "4",
                "is_valid": True,
            }
        ]
    }

    snap1 = persist_manual_submission_snapshot(
        instance_id=ws.instance_id,
        submission_id=submission.submission_id,
        accuracy_pct=100.0,
        details=details,
        db=db,
    )
    snap2 = persist_manual_submission_snapshot(
        instance_id=ws.instance_id,
        submission_id=submission.submission_id,
        accuracy_pct=100.0,
        details=details,
        db=db,
    )

    assert snap1.input_hash == snap2.input_hash


# ── US1: Submit answers ───────────────────────────────────────────────────────

def test_start_submission_creates_draft(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    assert sub.status == ManualSubmissionStatus.DRAFT


def test_start_submission_raises_for_unknown_worksheet(db: Database):
    with pytest.raises(WorksheetNotFoundError):
        start_submission("nonexistent", db=db)


def test_start_submission_raises_on_duplicate_confirmed(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    confirm_and_score(sub.submission_id, db=db)

    with pytest.raises(SubmissionAlreadyConfirmedError):
        start_submission(worksheet.instance_id, db=db)


def test_set_answers_and_confirm_scores_correctly(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    outcome = confirm_and_score(sub.submission_id, db=db)

    assert outcome.correct_count == len(worksheet.exercises)
    assert outcome.total_count == len(worksheet.exercises)
    assert outcome.accuracy_pct == 100.0


def test_bulk_answer_persistence_ordering(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, entry_mode=ManualEntryMode.BULK, db=db)
    raw_answers = ["999"] * len(worksheet.exercises)  # all wrong
    set_answers_on_draft(sub.submission_id, raw_answers, db=db)
    entries = db.get_manual_answer_entries(sub.submission_id)
    assert [e.slot_index for e in entries] == list(range(len(worksheet.exercises)))
    assert all(e.raw_value == "999" for e in entries)


def test_confirm_and_score_is_idempotent(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    outcome1 = confirm_and_score(sub.submission_id, db=db)

    # Confirming a confirmed submission raises
    with pytest.raises(SubmissionNotDraftError):
        confirm_and_score(sub.submission_id, db=db)

    # But the score snapshot was created only once
    snap = db.get_score_snapshot_by_submission_hash(sub.submission_id, outcome1.input_hash)
    assert snap is not None
    assert snap.accuracy_pct == outcome1.accuracy_pct


# ── US2: Review and correct before submission ─────────────────────────────────

def test_get_review_summary_has_correct_slot_count(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    rows = get_review_summary(sub.submission_id, db=db)
    assert len(rows) == len(worksheet.exercises)
    for i, row in enumerate(rows):
        assert row.slot_index == i
        assert row.problem_text == worksheet.exercises[i].problem_text


def test_update_single_answer_changes_slot_value(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)

    # Introduce a wrong answer at slot 0 then correct it
    update_single_answer(sub.submission_id, 0, "999", db=db)
    rows = get_review_summary(sub.submission_id, db=db)
    assert rows[0].raw_value == "999"

    update_single_answer(sub.submission_id, 0, correct_answers[0], db=db)
    rows = get_review_summary(sub.submission_id, db=db)
    assert rows[0].raw_value == correct_answers[0]

    # Score still correct after correction
    outcome = confirm_and_score(sub.submission_id, db=db)
    assert outcome.correct_count == len(worksheet.exercises)


def test_update_single_answer_rejects_confirmed(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    confirm_and_score(sub.submission_id, db=db)

    with pytest.raises(SubmissionNotDraftError):
        update_single_answer(sub.submission_id, 0, "1", db=db)


def test_resume_draft_returns_latest_draft(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    retrieved = resume_draft(worksheet.instance_id, db=db)
    assert retrieved.submission_id == sub.submission_id


def test_resume_draft_raises_when_none_exists(db: Database, worksheet):
    with pytest.raises(DraftNotFoundError):
        resume_draft(worksheet.instance_id, db=db)


def test_cancel_submission_marks_cancelled(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    cancel_submission(sub.submission_id, db=db)
    fetched = db.get_manual_submission(sub.submission_id)
    assert fetched.status == ManualSubmissionStatus.CANCELLED


# ── US3: Timing ───────────────────────────────────────────────────────────────

def test_confirm_persists_duration_seconds(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    correct_answers = [str(ex.answer) for ex in worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    outcome = confirm_and_score(sub.submission_id, duration_seconds=754, db=db)
    assert outcome.duration_seconds == 754

    confirmed = db.get_confirmed_manual_submission_for_instance(worksheet.instance_id)
    assert confirmed.duration_seconds == 754


def test_confirm_without_timing_is_valid(db: Database, worksheet):
    sub = start_submission(worksheet.instance_id, db=db)
    set_answers_on_draft(sub.submission_id, ["999"] * len(worksheet.exercises), db=db)
    outcome = confirm_and_score(sub.submission_id, db=db)
    assert outcome.duration_seconds is None


def test_confirm_and_score_ordering_sequences_correct(db: Database, ordering_worksheet):
    sub = start_submission(ordering_worksheet.instance_id, db=db)
    correct_answers = [ex.canonical_answer or "" for ex in ordering_worksheet.exercises]
    set_answers_on_draft(sub.submission_id, correct_answers, db=db)
    outcome = confirm_and_score(sub.submission_id, db=db)

    assert outcome.correct_count == len(ordering_worksheet.exercises)
    assert outcome.total_count == len(ordering_worksheet.exercises)
    assert outcome.accuracy_pct == 100.0


def test_confirm_and_score_ordering_sequences_wrong_order(db: Database, ordering_worksheet):
    sub = start_submission(ordering_worksheet.instance_id, db=db)
    wrong_answers: list[str] = []
    for ex in ordering_worksheet.exercises:
        nums = list(reversed(ex.prompt_numbers or []))
        wrong_answers.append(" ".join(str(n) for n in nums))

    set_answers_on_draft(sub.submission_id, wrong_answers, db=db)
    outcome = confirm_and_score(sub.submission_id, db=db)

    assert outcome.total_count == len(ordering_worksheet.exercises)
    assert outcome.correct_count < len(ordering_worksheet.exercises)



"""
Core domain models for the Kumon Agent.

All entities are Pydantic models so they can be:
- Validated at creation time
- Serialised to/from JSON for persistence
- Shared between CLI, FastAPI routes, and domain services

Design notes
------------
- No ORM mapping here — persistence is a separate concern (app/persistence/).
- ChildProfile, WorksheetInstance, etc. are value objects: immutable after
  creation unless explicitly rebuilt.
- Greek strings (_el suffix) are used for child-facing content.
- Constitutional Principle II: arithmetic answers are always Python ints/floats,
  never LLM-generated strings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────


class SkillId(str, Enum):
    """Top-level skill categories, aligned with the Greek school curriculum."""

    NUMBER_SENSE = "number_sense"
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"
    FRACTIONS = "fractions"
    WORD_PROBLEMS = "word_problems"
    PLACE_VALUE = "place_value"


class MicroSkillId(str, Enum):
    """
    Fine-grained practice targets within a skill.

    Each micro-skill maps to a specific set of exercise generation rules in
    app/domain/math_engine.py.  The difficulty_level field in MicroSkillMeta
    governs ordering within a skill (1 = easiest, 10 = hardest).
    """

    # Addition
    ADDITION_SINGLE_DIGIT = "addition_single_digit"
    ADDITION_TWO_DIGIT_NO_CARRY = "addition_two_digit_no_carry"
    ADDITION_WITH_CARRYING = "addition_with_carrying"
    ADDITION_THREE_NUMBERS = "addition_three_numbers"

    # Subtraction
    SUBTRACTION_SINGLE_DIGIT = "subtraction_single_digit"
    SUBTRACTION_TWO_DIGIT_NO_BORROW = "subtraction_two_digit_no_borrow"
    SUBTRACTION_WITH_BORROWING = "subtraction_with_borrowing"

    # Multiplication
    MULTIPLICATION_2_5 = "multiplication_2_5"
    MULTIPLICATION_6_9 = "multiplication_6_9"
    MULTIPLICATION_MIXED = "multiplication_mixed"

    # Division
    DIVISION_2_5 = "division_2_5"
    DIVISION_6_9 = "division_6_9"
    DIVISION_MIXED = "division_mixed"

    # Number sense
    HALF_AND_DOUBLE = "half_and_double"
    ORDERING_NUMBERS = "ordering_numbers"


class WorksheetType(str, Enum):
    """
    Worksheet type controls the exercise selection strategy.

    See KumonKnowledgeBase.get_worksheet_type_guide() for full descriptions.
    """

    DRILL = "drill"
    MIXED_REVIEW = "mixed_review"
    CORRECTION = "correction"
    TIMED_FLUENCY = "timed_fluency"
    CONCEPT_REINFORCEMENT = "concept_reinforcement"


class Operator(str, Enum):
    """Mathematical operators used in exercise display."""

    ADD = "+"
    SUBTRACT = "−"
    MULTIPLY = "×"
    DIVIDE = "÷"


class SubmissionStatus(str, Enum):
    """Lifecycle status of an uploaded worksheet artifact."""

    UPLOADED = "uploaded"
    OCR_PROCESSED = "ocr_processed"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
    SCORED = "scored"
    FAILED = "failed"


class OcrResultStatus(str, Enum):
    """Review lifecycle for OCR results."""

    INGESTED = "ingested"
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    MISMATCHED = "mismatched"
    FAILED = "failed"
    REVIEWED = "reviewed"
    SCORED = "scored"


_OCR_STATUS_TRANSITIONS: dict[OcrResultStatus, set[OcrResultStatus]] = {
    OcrResultStatus.INGESTED: {OcrResultStatus.EXTRACTED},
    OcrResultStatus.EXTRACTED: {
        OcrResultStatus.NEEDS_REVIEW,
        OcrResultStatus.MISMATCHED,
        OcrResultStatus.FAILED,
    },
    OcrResultStatus.NEEDS_REVIEW: {OcrResultStatus.REVIEWED},
    OcrResultStatus.MISMATCHED: {OcrResultStatus.REVIEWED},
    OcrResultStatus.REVIEWED: {OcrResultStatus.SCORED},
    OcrResultStatus.FAILED: set(),
    OcrResultStatus.SCORED: set(),
}


def can_transition_ocr_status(current: OcrResultStatus, target: OcrResultStatus) -> bool:
    """Return True when an OCR status transition is allowed by the lifecycle."""
    return target in _OCR_STATUS_TRANSITIONS[current]


class OcrValueSource(str, Enum):
    """Whether a value came from OCR directly or a parent correction."""

    OCR = "ocr"
    MANUAL = "manual"


class ManualSubmissionStatus(str, Enum):
    """Lifecycle state for parent-entered manual submissions."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ManualEntryMode(str, Enum):
    """How parent provided answers in a manual submission session."""

    SEQUENTIAL = "sequential"
    BULK = "bulk"


# ── Core entities ─────────────────────────────────────────────────────────────


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Exercise(BaseModel):
    """
    A single arithmetic exercise.

    The answer is always computed by Python code (math_engine.py), never by
    the LLM.  Constitutional Principle II.
    """

    exercise_id: str = Field(default_factory=_new_id)
    operand_a: int | float
    operand_b: int | float
    operator: Operator
    answer: int | float
    # Display strings — formatted for the child
    problem_text: str  # e.g. "7 × 8 = ___"
    answer_text: str   # e.g. "7 × 8 = 56"
    micro_skill_id: MicroSkillId


class ChildProfile(BaseModel):
    """
    Represents the child being tutored.

    A single default profile is created automatically on first run.
    The parent can create named profiles via the CLI or web UI.
    """

    child_id: str = Field(default_factory=_new_id)
    display_name: str
    age: int = Field(ge=4, le=18)
    grade_level: int = Field(ge=1, le=12)
    locale: str = "el-GR"
    language: str = "el"
    preferred_sheet_length: int = Field(default=15, ge=5, le=40)
    timing_enabled: bool = False
    review_mix_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    notes: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class WorksheetInstance(BaseModel):
    """
    A generated worksheet ready for printing.

    Stores the complete exercise set plus metadata so scoring can later
    be linked unambiguously back to this specific sheet.
    Constitutional Principle: Never lose the linkage between worksheet,
    submission, and decision.
    """

    instance_id: str = Field(default_factory=_new_id)
    child_id: str | None = None
    micro_skill_id: MicroSkillId
    worksheet_type: WorksheetType = WorksheetType.DRILL
    exercises: list[Exercise]
    # Greek-language display strings
    title_el: str
    instructions_el: str
    created_at: datetime = Field(default_factory=_now)
    # Set after HTML files are written
    html_path: str | None = None
    answer_key_path: str | None = None
    # Seed used for exercise generation — enables reproducible regeneration
    seed: int | None = None


class MicroSkillMeta(BaseModel):
    """
    Catalogue entry for a micro-skill.

    This is the schema for the built-in skill catalogue in knowledge_base.py.
    It is also what the CLI `list-skills` and `explain skill` commands display.
    """

    micro_skill_id: MicroSkillId
    parent_skill_id: SkillId
    name_en: str
    name_el: str
    description_en: str
    description_el: str
    difficulty_level: int = Field(ge=1, le=10)
    prerequisites: list[MicroSkillId] = Field(default_factory=list)


class ProgressDecision(BaseModel):
    """
    The outcome of the progression planner for a single worksheet cycle.

    Every decision must be deterministic, machine-readable, and auditable.
    Constitutional Principle III.
    """

    decision_id: str = Field(default_factory=_new_id)
    child_id: str
    from_micro_skill_id: MicroSkillId
    next_micro_skill_id: MicroSkillId
    action: str  # "advance" | "stay" | "step_back"
    reason: str  # Human-readable explanation (English, for developer/audit)
    reason_el: str  # Greek explanation for parent UI
    accuracy_pct: float
    created_at: datetime = Field(default_factory=_now)
    parent_override: bool = False
    override_note: str = ""


class WorksheetSubmission(BaseModel):
    """One uploaded worksheet artifact linked to a generated worksheet instance."""

    submission_id: str = Field(default_factory=_new_id)
    instance_id: str
    child_id: str | None = None
    file_path: str
    mime_type: str
    file_hash: str
    uploaded_at: datetime = Field(default_factory=_now)
    status: SubmissionStatus = SubmissionStatus.UPLOADED
    failure_reason: str | None = None


class OcrResult(BaseModel):
    """Container model for OCR output tied to one submission."""

    ocr_result_id: str = Field(default_factory=_new_id)
    submission_id: str
    instance_id: str
    engine: str = "hybrid"
    engine_version: str = "unknown"
    fallback_model: str | None = None
    confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    status: OcrResultStatus = OcrResultStatus.INGESTED
    created_at: datetime = Field(default_factory=_now)
    reviewed_at: datetime | None = None


class OcrField(BaseModel):
    """Per-exercise extracted answer plus manual correction metadata."""

    ocr_field_id: str = Field(default_factory=_new_id)
    ocr_result_id: str
    exercise_id: str
    slot_index: int = Field(ge=0)
    raw_value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False
    original_ocr_value: str | None = None
    corrected_value: str | None = None
    value_source: OcrValueSource = OcrValueSource.OCR
    bbox: str | None = None
    updated_at: datetime = Field(default_factory=_now)


class ManualSubmission(BaseModel):
    """Parent-entered submission session linked to one worksheet."""

    submission_id: str = Field(default_factory=_new_id)
    instance_id: str
    child_id: str | None = None
    status: ManualSubmissionStatus = ManualSubmissionStatus.DRAFT
    entry_mode: ManualEntryMode = ManualEntryMode.SEQUENTIAL
    duration_seconds: int | None = Field(default=None, ge=0)
    confirmed_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ManualAnswerEntry(BaseModel):
    """One manually entered answer aligned to worksheet slot order."""

    answer_entry_id: str = Field(default_factory=_new_id)
    submission_id: str
    exercise_id: str
    slot_index: int = Field(ge=0)
    raw_value: str
    normalized_value: str
    is_valid: bool = True
    updated_at: datetime = Field(default_factory=_now)


class ScoreResultSnapshot(BaseModel):
    """Immutable deterministic score record from reviewed OCR values."""

    score_result_id: str = Field(default_factory=_new_id)
    instance_id: str
    ocr_result_id: str | None = None
    submission_id: str | None = None
    input_hash: str
    accuracy_pct: float
    details_json: str
    created_at: datetime = Field(default_factory=_now)



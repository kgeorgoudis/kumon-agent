# Data Model: Ordering Numbers Skill

## Overview

This feature extends the existing worksheet and submission model so one `Exercise` can represent either a scalar arithmetic problem or an ordering-sequence problem. No separate worksheet type or persistence table is required.

## Existing Entities Used

### WorksheetInstance (existing)

- **Purpose**: Stores the generated worksheet, including every exercise and display metadata.
- **Relevant fields**:
  - `instance_id: str`
  - `micro_skill_id: MicroSkillId`
  - `exercises: list[Exercise]`
  - `title_el: str`
  - `instructions_el: str`
  - `seed: int | None`

### ManualSubmission (existing)

- **Purpose**: Parent-confirmed answer set for a worksheet.
- **Relevant fields**:
  - `submission_id: str`
  - `instance_id: str`
  - `status: ManualSubmissionStatus`
  - `entry_mode: ManualEntryMode`
  - `duration_seconds: int | None`

### ManualAnswerEntry (existing)

- **Purpose**: Stores one raw and normalized answer per exercise slot.
- **Relevant fields**:
  - `submission_id: str`
  - `exercise_id: str`
  - `slot_index: int`
  - `raw_value: str`
  - `normalized_value: str`
  - `is_valid: bool`

### ScoreResultSnapshot (existing)

- **Purpose**: Immutable deterministic scoring record.
- **Relevant fields**:
  - `score_result_id: str`
  - `instance_id: str`
  - `submission_id: str | None`
  - `input_hash: str`
  - `accuracy_pct: float`
  - `details_json: str`

## Entity Changes

### Exercise (extended existing entity)

- **Purpose**: Unified worksheet item model for both arithmetic and ordering skills.
- **Existing fields retained**:
  - `exercise_id: str`
  - `problem_text: str`
  - `answer_text: str`
  - `micro_skill_id: MicroSkillId`
- **Existing arithmetic-centric fields that remain for backward compatibility**:
  - `operand_a: int | float`
  - `operand_b: int | float`
  - `operator: Operator`
  - `answer: int | float`
- **New optional ordering fields**:
  - `prompt_numbers: list[int] | None` — the unsorted source numbers shown to the child
  - `ordering_direction: Literal["ascending", "descending"] | None`
  - `canonical_answer: str | None` — normalized expected sequence, e.g. `"5 17 42 108"`

## Derived Rules

- `ordering_exercise := exercise.micro_skill_id == ordering_numbers`
- `expected_answer(exercise)`:
  - arithmetic worksheet -> `str(exercise.answer)`
  - ordering worksheet -> `exercise.canonical_answer`
- `normalized_ordering_submission(raw)`:
  - extract integer tokens in entered order
  - join with one ASCII space
  - mark invalid if fewer than 2 numeric tokens are present

## Validation Rules

- Ordering exercises MUST contain 4-6 distinct integers (`FR-001`, `FR-002`).
- Ordering exercise integers MUST be within the configured feature range (<=1000 for v1) (`FR-003`).
- `ordering_direction` MUST be either `ascending` or `descending` for `ordering_numbers` exercises (`FR-005`).
- `canonical_answer` MUST reflect the correctly ordered sequence for the stored `prompt_numbers` (`FR-006`, `SC-002`).
- Non-ordering exercises may leave ordering-specific fields unset.
- Manual submission normalization for ordering exercises MUST preserve child-entered order and MUST NOT auto-sort it during scoring (`FR-008`).

## Relationships

- One `WorksheetInstance` contains many `Exercise` records serialized in `exercises_json`.
- One `ManualSubmission` has up to one `ManualAnswerEntry` per exercise slot.
- One confirmed `ManualSubmission` yields one `ScoreResultSnapshot` per unique scoring input hash.

## State Semantics

No new persistence lifecycle is added. Existing submission/scoring states remain unchanged.

Runtime scoring branch:

- arithmetic exercise -> scalar normalization + numeric-aware comparison
- ordering exercise -> sequence normalization + canonical string comparison

## Compatibility Notes

- Existing persisted worksheets continue to deserialize because new ordering-specific fields are optional.
- Existing arithmetic scoring remains unchanged except for a new branch when the worksheet micro-skill is `ordering_numbers`.


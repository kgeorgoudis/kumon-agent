# Data Model: Remove OCR Capability

## Overview

This feature is subtractive: it removes OCR domain entities and preserves the manual submission data model as the sole scored worksheet pathway.

## Retained Entities

### ChildProfile
- Purpose: identifies a child and worksheet preferences.
- Key fields: `child_id`, `display_name`, `age`, `grade_level`, `locale`, `language`, `preferred_sheet_length`.
- Relationships:
  - `ChildProfile (1) -> (N) WorksheetInstance`
  - `ChildProfile (1) -> (N) ManualSubmission`

### WorksheetInstance
- Purpose: generated printable worksheet with deterministic exercise payload.
- Key fields: `instance_id`, `child_id`, `micro_skill_id`, `worksheet_type`, `exercises`, `title_el`, `instructions_el`, `seed`.
- Relationships:
  - `WorksheetInstance (1) -> (N) ManualSubmission`

### ManualSubmission
- Purpose: parent-entered submission session for one worksheet.
- Key fields: `submission_id`, `instance_id`, `child_id`, `status`, `entry_mode`, `duration_seconds`, `confirmed_at`.
- Status transitions:
  - `draft -> confirmed`
  - `draft -> cancelled`
- Validation:
  - `duration_seconds >= 0` when present.

### ManualAnswerEntry
- Purpose: one manual answer per worksheet slot.
- Key fields: `answer_entry_id`, `submission_id`, `exercise_id`, `slot_index`, `raw_value`, `normalized_value`, `is_valid`.
- Validation:
  - `slot_index >= 0`
  - unique `(submission_id, slot_index)` in persistence.

### ScoreResultSnapshot
- Purpose: immutable deterministic score output linked to manual submission input hash.
- Key fields: `score_result_id`, `instance_id`, `submission_id`, `input_hash`, `accuracy_pct`, `details_json`, `created_at`.
- Change in this feature:
  - removed model field `ocr_result_id` from domain model.

## Removed Entities

### OcrResult (removed)
- Reason: OCR ingestion/review workflow removed.

### OcrField (removed)
- Reason: per-slot OCR extraction and correction no longer supported.

### OcrResultStatus / OcrValueSource (removed)
- Reason: OCR lifecycle and value provenance types no longer used.

### WorksheetSubmission / SubmissionStatus (removed)
- Reason: upload artifact workflow removed from active model; manual submission is the only supported path.

## Persistence Notes

- Legacy schema objects (`ocr_results`, `ocr_fields`, `worksheet_submissions`, and `score_result_snapshots.ocr_result_id`) are retained for backward-compatible database opening.
- Active runtime reads/writes are manual-submission-centric.
- Progress reporting now depends on snapshots linked by `submission_id`.


# CLI Contract (Manual-Only Submission)

## Scope

Defines the supported CLI behavior after OCR removal.

## Supported Commands

### `kumon submit <instance_id>`

- Purpose: parent manually enters worksheet answers and triggers deterministic scoring.
- Inputs:
  - required: `instance_id`
  - optional: `--answers`, `--time`, `--resume`, `--no-confirm`
- Output contract:
  - Creates/updates a `ManualSubmission`.
  - Persists `ManualAnswerEntry` rows by slot order.
  - On confirmation, persists deterministic `ScoreResultSnapshot` linked by `submission_id`.
  - Prints result panel with `correct_count`, `total_count`, `accuracy_pct`, optional duration.
- Error contract:
  - Invalid worksheet id -> `ERR_WORKSHEET_NOT_FOUND`
  - Invalid answer count/format -> `ERR_ANSWER_COUNT_MISMATCH` or `ERR_INVALID_ANSWER_FORMAT`
  - Invalid duration -> `ERR_INVALID_DURATION_FORMAT`

### `kumon pending`

- Purpose: list worksheets without confirmed manual submission.
- Output contract:
  - Returns pending worksheet rows with draft-state indicators.

### `kumon progress`

- Purpose: show progress from confirmed scored manual submissions.
- Output contract:
  - Includes only manual-submission-linked score snapshots.
  - Optional LLM narrative remains best-effort/degraded.

## Removed CLI Surface

- No OCR CLI commands are supported.
- No upload/image/PDF ingestion command is supported as part of worksheet scoring flow.


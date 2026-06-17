# Data Model - Manual Exercise Ingestion by Parent

## Entities

### WorksheetInstance (existing)
- **Purpose**: Source worksheet definition for manual submission and deterministic scoring.
- **Key fields used by this feature**:
  - `instance_id` (PK)
  - `child_id`
  - `exercises[]` (ordered problems with deterministic `answer`)
  - `created_at`

### ManualSubmission (new)
- **Purpose**: Parent-confirmed or in-progress answer entry session for one worksheet.
- **Fields**:
  - `submission_id` (PK, UUID)
  - `instance_id` (FK -> `WorksheetInstance.instance_id`, required)
  - `child_id` (nullable, denormalized from worksheet)
  - `status` (`draft` | `confirmed` | `cancelled`)
  - `entry_mode` (`sequential` | `bulk`)
  - `duration_seconds` (nullable int, optional timing)
  - `confirmed_at` (nullable datetime)
  - `created_at` (datetime)
  - `updated_at` (datetime)
- **Validation rules**:
  - Only one `confirmed` submission allowed per `instance_id`.
  - `duration_seconds` must be `>= 0` when present.
  - `confirmed_at` required when `status=confirmed`.

### ManualAnswerEntry (new)
- **Purpose**: One entered answer mapped to one worksheet exercise slot.
- **Fields**:
  - `answer_entry_id` (PK, UUID)
  - `submission_id` (FK -> `ManualSubmission.submission_id`)
  - `exercise_id` (required)
  - `slot_index` (0-based index aligned to worksheet exercise ordering)
  - `raw_value` (string as parent typed)
  - `normalized_value` (string used for deterministic scoring)
  - `is_valid` (bool, local validation result)
  - `updated_at` (datetime)
- **Validation rules**:
  - Unique key: (`submission_id`, `slot_index`).
  - `slot_index` range must match worksheet exercise count.
  - `normalized_value` generated deterministically from `raw_value`.

### ScoreResultSnapshot (existing, adapted linkage)
- **Purpose**: Immutable deterministic scoring output for one confirmed submission.
- **Fields impacted**:
  - `score_result_id` (PK)
  - `instance_id`
  - `submission_id` (new FK for manual flow)
  - `input_hash` (stable hash of normalized answers + worksheet context)
  - `accuracy_pct`
  - `details_json`
  - `created_at`
- **Validation rules**:
  - Unique key: (`submission_id`, `input_hash`) for idempotent rescoring.

## Relationships

- `WorksheetInstance (1) -> (N) ManualSubmission`
- `ManualSubmission (1) -> (N) ManualAnswerEntry`
- `ManualSubmission (1) -> (N) ScoreResultSnapshot`
- `WorksheetInstance (1) -> (N) ScoreResultSnapshot`

## State Transitions

### ManualSubmission lifecycle
- `draft -> confirmed`
- `draft -> cancelled`
- `confirmed` and `cancelled` are terminal.

### Operational scoring transition
- On `draft -> confirmed`, scoring runs automatically once and writes a `ScoreResultSnapshot`.
- Re-running deterministic scoring with unchanged normalized answers returns the existing snapshot (same `input_hash`).

## Persistence Notes

- Keep append-friendly history by creating new submissions instead of mutating confirmed records.
- Store per-answer entries separately (not only a JSON blob) to support review, correction, and future analytics.
- Preserve clear lineage keys so planner/mastery modules can trace `worksheet -> submission -> score` without OCR tables.


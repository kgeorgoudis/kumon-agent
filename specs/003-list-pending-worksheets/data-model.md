# Data Model: List Pending Worksheets

## Overview

This feature introduces a read model for pending worksheet listing. No new core domain entity is required; the feature derives state from existing `WorksheetInstance` + `ManualSubmission` records.

## Entities In Scope

### WorksheetInstance (existing)

- **Purpose**: Generated worksheet artifact to be solved on paper.
- **Relevant fields**:
  - `instance_id: str`
  - `child_id: str | None`
  - `title_el: str`
  - `created_at: datetime`
  - `exercises: list[Exercise]` (count used for display)

### ManualSubmission (existing)

- **Purpose**: Parent-entered submission lifecycle for a worksheet.
- **Relevant fields**:
  - `submission_id: str`
  - `instance_id: str`
  - `status: ManualSubmissionStatus` (`draft`, `confirmed`, `cancelled`)
  - `updated_at: datetime`
  - `confirmed_at: datetime | None`

## Derived Read Model

### PendingWorksheetRow (new projection/value object)

- **Purpose**: Terminal-friendly row returned for `kumon pending`.
- **Fields**:
  - `instance_id: str` (full copyable identifier)
  - `child_id: str | None`
  - `title_el: str`
  - `created_at: datetime`
  - `exercise_count: int`
  - `has_draft_submission: bool`
  - `latest_draft_submission_id: str | None`

## Derived Rules

- `is_pending(instance_id) := NOT EXISTS manual_submissions WHERE instance_id = ? AND status = 'confirmed'`
- `has_draft_submission(instance_id) := EXISTS manual_submissions WHERE instance_id = ? AND status = 'draft'`

## Validation Rules

- Pending list MUST exclude worksheets with any confirmed submission (`FR-001`, `FR-005`).
- Pending list MUST include worksheets with only draft/cancelled submissions (`FR-005`).
- Returned rows MUST be ordered by `worksheet_instances.created_at DESC` (`FR-007`).
- `instance_id` MUST be preserved as full-length value in output (`FR-006`).
- Optional child filter MUST match by resolved `child_id` only (`FR-003`).

## State Semantics

No new state transitions are introduced. This feature reads existing lifecycle state:

- `no manual_submissions` => pending
- `draft only` => pending (`has_draft_submission = true`)
- `cancelled only` => pending
- `confirmed present` => not pending


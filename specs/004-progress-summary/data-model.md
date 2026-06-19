# Data Model: Progress Summary

## Overview

This feature adds deterministic read models for progress analytics and an optional LLM narrative layer. No arithmetic or scoring rules are moved to prompts.

## Existing Entities Used

### WorksheetInstance (existing)

- **Purpose**: Source for worksheet metadata and micro-skill identifiers.
- **Relevant fields**:
  - `instance_id: str`
  - `child_id: str | None`
  - `micro_skill_id: MicroSkillId`
  - `title_el: str`
  - `created_at: datetime`

### ManualSubmission (existing)

- **Purpose**: Lifecycle boundary for confirmed parent submissions.
- **Relevant fields**:
  - `submission_id: str`
  - `instance_id: str`
  - `child_id: str | None`
  - `status: ManualSubmissionStatus` (must be `confirmed`)
  - `confirmed_at: datetime | None`

### ScoreResultSnapshot (existing)

- **Purpose**: Deterministic score result per submission/input hash.
- **Relevant fields**:
  - `score_result_id: str`
  - `instance_id: str`
  - `submission_id: str | None`
  - `accuracy_pct: float`
  - `details_json: str`
  - `created_at: datetime`

## New Derived Value Objects

### ProgressWorksheetPoint

- **Purpose**: One chronological row in the progress timeline.
- **Fields**:
  - `instance_id: str`
  - `submission_id: str`
  - `child_id: str | None`
  - `micro_skill_id: str`
  - `title_el: str`
  - `accuracy_pct: float`
  - `correct_count: int`
  - `total_count: int`
  - `confirmed_at: datetime`

### SkillProgress

- **Purpose**: Per-micro-skill aggregate performance.
- **Fields**:
  - `micro_skill_id: str`
  - `worksheet_count: int`
  - `avg_accuracy_pct: float`
  - `last_accuracy_pct: float`
  - `trend: str` (`improving` | `stable` | `declining`)

### ProgressSuggestion

- **Purpose**: One actionable suggestion for the parent.
- **Fields**:
  - `target_micro_skill_id: str | None`
  - `suggested_worksheet_type: str | None`
  - `rationale_el: str`
  - `confidence: str | None`

### ProgressReport

- **Purpose**: Parent-facing report payload for CLI and web.
- **Fields**:
  - `child_id: str`
  - `child_display_name: str`
  - `worksheet_count: int`
  - `date_from: datetime`
  - `date_to: datetime`
  - `overall_accuracy_pct: float`
  - `overall_trend: str` (`improving` | `stable` | `declining` | `insufficient_data`)
  - `skill_progress: list[SkillProgress]`
  - `narrative_status: str` (`generated` | `degraded` | `not_requested`)
  - `summary_el: str | None`
  - `suggestions: list[ProgressSuggestion]`
  - `llm_error_code: str | None`
  - `prompt_version: str`

## Derived Rules

- `report_rows := confirmed_manual_submissions JOIN worksheet_instances JOIN score_result_snapshots`
- `overall_accuracy_pct := mean(point.accuracy_pct for point in report_rows)`
- `overall_trend := deterministic window comparison over chronological accuracy values`
- `skill_progress.avg_accuracy_pct := mean(accuracy_pct grouped by micro_skill_id)`
- `narrative_status = degraded` when LLM is unavailable or response is invalid; deterministic metrics remain present.

## Validation Rules

- Only confirmed submissions contribute to progress (`FR-001`, `FR-002`).
- Suggested micro-skills must exist in computed skill set or immediate curriculum neighbors (`FR-005`, `SC-003`).
- LLM output must parse into expected structured schema before use (`FR-003`, `FR-004`).
- If no scored worksheets exist, report returns no-data state with friendly Greek message (`User Story 1, Scenario 3`).
- Prompt version is always attached to output (`FR-010`).

## State Semantics

No new persistence lifecycle is added. Report generation has runtime-only states:

- `not_requested` -> deterministic report without LLM narrative.
- `generated` -> deterministic report + valid LLM summary and suggestions.
- `degraded` -> deterministic report + fallback narrative due to LLM failure/timeout/invalid response.


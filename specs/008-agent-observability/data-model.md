# Data Model: Agent Observability and Traceability

**Feature**: Agent Observability and Traceability (`008-agent-observability`)  
**Date**: 2026-06-27  
**Phase**: 1 (Design)

---

## Overview

The observability layer defines trace entity models and retrieval filters. Trace entities are extensions/alignments with existing Pydantic models in `app/domain/models.py` (TutorTaskState, TutorStepTrace) and are persisted to SQLite via the observability storage layer.

---

## Entities

### TutorTaskState (Existing in models.py, Reused)

**Purpose**: Represents one tutor task execution (run).

**Fields**:
- `task_id: str` — Unique identifier (UUID4), generated at run start
- `task_type: TutorTaskType` — Enum: PROGRESS_REPORT | WORKSHEET_REVIEW | NEXT_STEP_PLANNING
- `child_id: str | None` — Optional link to child profile
- `prompt_version: str` — Versioned prompt identifier (e.g., `v1/progress_summary`)
- `status: TutorTaskStatus` — Enum: INITIALIZED | GROUNDING | REASONING | VALIDATING | COMPLETED | DEGRADED | FAILED
- `deterministic_context: dict[str, Any]` — Sanitized task inputs (skill_id, accuracy threshold, etc., NO child name)
- `model_context: dict[str, Any]` — LLM-specific context if needed
- `output: dict[str, Any]` — Final task output (structured JSON)
- `error_code: str | None` — Machine-readable error (e.g., `LLM_TIMEOUT`, `VALIDATION_FAILED`)
- `created_at: datetime` — Run start time (UTC)
- `updated_at: datetime` — Last status transition time (UTC)

**Validation**:
- `task_id` must be non-empty UUID
- `status` transitions follow state machine (see State Transitions below)
- `error_code` required if `status == FAILED` or `status == DEGRADED`

**Storage**: `tutor_task_state` table (primary key: `task_id`)

---

### TutorStepTrace (Existing in models.py, Reused)

**Purpose**: Represents one step/node execution within a tutor task.

**Fields**:
- `step_id: str` — Unique identifier (UUID4)
- `task_id: str` — Foreign key to parent TutorTaskState
- `step_name: str` — Node name in agent graph (e.g., `ground_context`, `invoke_llm`, `validate_output`)
- `status: TutorStepStatus` — Enum: QUEUED | RUNNING | SUCCEEDED | FAILED | SKIPPED
- `input_snapshot: dict[str, Any]` — Sanitized step input (depends on step type)
- `output_snapshot: dict[str, Any]` — Sanitized step output (depends on step type)
- `error_code: str | None` — Optional error if status == FAILED
- `started_at: datetime` — Step execution start (UTC)
- `finished_at: datetime | None` — Step execution end (UTC), null if in progress

**Validation**:
- `task_id` must reference existing TutorTaskState
- `status` transitions: QUEUED → RUNNING → (SUCCEEDED | FAILED | SKIPPED)
- `finished_at` required if status != RUNNING or QUEUED

**Storage**: `tutor_step_trace` table (primary key: `step_id`, foreign key: `task_id`)

---

### TraceRetrievalFilter

**Purpose**: Query specification for trace retrieval (no persistence; used for CLI/API filtering).

**Fields**:
- `status: TutorTaskStatus | None` — Filter by run status; null = all statuses
- `task_type: TutorTaskType | None` — Filter by task type; null = all types
- `hours_since: int` — Return runs created in last N hours (default: 24)
- `limit: int` — Max results to return (default: 50, max: 500)
- `offset: int` — Pagination offset (default: 0)
- `sort_by: str` — Sort field: `created_at` (default, newest first) | `status`

**Usage example**:
```python
filter = TraceRetrievalFilter(
    status=TutorTaskStatus.DEGRADED,
    task_type=TutorTaskType.PROGRESS_REPORT,
    hours_since=6,
    limit=20
)
```

---

## State Machines

### Run Status Lifecycle

```
INITIALIZED
    ↓
GROUNDING (gathering deterministic context)
    ↓
REASONING (LLM reasoning or deterministic logic)
    ↓
VALIDATING (checking output quality)
    ↓
┌→ COMPLETED (success)
│
├→ DEGRADED (partial success, fallback used)
│
└→ FAILED (error, no valid output)
```

**Transitions**:
- `INITIALIZED → GROUNDING` (automatic on run start)
- `GROUNDING → REASONING` or `REASONING` (skip grounding if cached)
- `REASONING → VALIDATING` (before output returned)
- `VALIDATING → COMPLETED` (if validation passes)
- `VALIDATING → DEGRADED` (if validation fails but fallback available)
- Any state → `FAILED` (on unrecoverable error)

**Note**: A run that transitions to DEGRADED still produces valid output; error_code documents the reason (e.g., `LLM_TIMEOUT`, `VALIDATION_FAILED`).

### Step Status Lifecycle

```
QUEUED
    ↓
RUNNING
    ↓
┌→ SUCCEEDED
│
├→ FAILED (error, no output)
│
└→ SKIPPED (conditionally bypassed)
```

**Transitions**:
- Step created in QUEUED state
- Step transitions to RUNNING when execution starts
- Step transitions to one of SUCCEEDED | FAILED | SKIPPED when execution completes

---

## Relationships

**TutorTaskState ← (1:N) → TutorStepTrace**

- One run contains 0 or more steps
- Every step belongs to exactly one run (foreign key: `task_id`)
- Steps are ordered by `started_at` and `step_id` (creation order)
- Retrieval may return run + step timeline together

**Example run with steps**:
```
Task: task_id=abc123, status=COMPLETED, prompt_version=v1/progress_summary
  Step 1: ground_context, SUCCEEDED, started_at=T0, finished_at=T1
  Step 2: invoke_llm, SUCCEEDED, started_at=T1, finished_at=T3
  Step 3: validate_output, SUCCEEDED, started_at=T3, finished_at=T4
```

---

## Sanitization Policy

All trace entities apply sanitization rules at **emission time** (when written to storage):

### Rule Set

1. **Deterministic Context**:
   - ✅ Include: skill_id, exercise_count, accuracy_threshold, mastery_level
   - ❌ Exclude: child name, age, grade level, parent name

2. **Model Context**:
   - ✅ Include: prompt_version, model_name, temperature setting
   - ❌ Exclude: full prompt text, API keys

3. **Output Snapshot**:
   - ✅ Include: summary of recommendations (count, types), status flags
   - ❌ Exclude: full narrative text (store only aggregate metrics)

4. **Input/Output Snapshots**:
   - ✅ Include: field names, types, lengths
   - ❌ Exclude: raw values for PII fields (child name, answers, etc.)

### Implementation

**SanitizationPolicy** (enum in `app/observability/models.py`):
```python
class SanitizationPolicy(str, Enum):
    DETERMINISTIC_ONLY = "deterministic_only"  # No LLM data
    SUMMARY_ONLY = "summary_only"              # Aggregated metrics only
    FULL = "full"                              # Complete snapshots (testing only)
```

**Sanitizer function** (in `app/observability/storage.py`):
```python
def sanitize_context(raw_context: dict, policy: SanitizationPolicy) -> dict:
    """Remove PII/secrets from deterministic context."""
    ...
```

**Testing**: Unit tests in `test_observability_models.py` verify that sanitized records do not contain child names or other PII.

---

## Indexes

**tutor_task_state**:
- Primary: `task_id`
- Secondary:
  - `(status)` — fast filtering by COMPLETED | DEGRADED | FAILED
  - `(task_type)` — fast filtering by task type
  - `(created_at DESC)` — chronological retrieval (newest first)
  - `(status, task_type, created_at)` — composite for complex filters

**tutor_step_trace**:
- Primary: `step_id`
- Foreign key: `task_id`
- Secondary:
  - `(task_id, started_at)` — retrieve all steps for a run in order

---

## Next Steps

- **Contracts**: Define CLI commands and HTTP API endpoints for trace retrieval
- **Quickstart**: Document how to emit traces from agent graph, query with TraceService, inspect via CLI/web
- **Tests**: Implement trace model validation, sanitization, state machine enforcement


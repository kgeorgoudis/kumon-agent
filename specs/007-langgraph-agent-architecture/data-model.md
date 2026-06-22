# Data Model: LangGraph Agentic Architecture

**Feature**: `007-langgraph-agent-architecture`
**Date**: 2026-06-22

## Overview

This feature adds agent-specific runtime concepts around the existing tutor workflows.
The goal is to make LangGraph orchestration inspectable while keeping all domain truth
in existing deterministic services.

## Entities

### 1. `TutorTaskState`

Represents the working state for one agent run.

**Fields**
- `task_id`: unique identifier for the run
- `task_type`: `progress_report` | `worksheet_review` | `next_step_planning`
- `child_id`: child profile identifier
- `prompt_version`: versioned persona/task prompt reference
- `status`: `initialized` | `grounding` | `reasoning` | `validating` | `completed` | `degraded` | `failed`
- `deterministic_context`: structured facts from services/domain code
- `model_context`: sanitized model inputs used for narrative generation
- `output`: structured final result (summary, suggestions, metadata)
- `error_code`: optional failure code when degraded/failed
- `created_at`: timestamp
- `updated_at`: timestamp

**Validation rules**
- `task_type` must map to a supported tutor responsibility.
- `prompt_version` must reference a versioned prompt file.
- `deterministic_context` must only contain code-owned facts.
- `output` must be schema-valid before status can become `completed`.

**Relationships**
- Belongs to one `ChildProfile`.
- Produces one or more `TutorStepTrace` rows.
- May reference one or more `ProgressWorksheetPoint`, `ProgressDecision`, or `ScoreResultSnapshot` records through its grounded facts.

### 2. `TutorStepTrace`

Represents one explicit step in the LangGraph flow.

**Fields**
- `step_id`: unique identifier
- `task_id`: parent `TutorTaskState` identifier
- `step_name`: English step label such as `collect_progress_facts` or `compose_summary`
- `status`: `queued` | `running` | `succeeded` | `failed` | `skipped`
- `input_snapshot`: compact JSON snapshot of the step input
- `output_snapshot`: compact JSON snapshot of the step output
- `error_code`: optional failure code
- `started_at`: timestamp
- `finished_at`: timestamp

**Validation rules**
- `step_name` must be stable across runs for the same graph version.
- `input_snapshot` and `output_snapshot` should be compact and schema-aware, not raw verbose logs.
- A terminal `TutorTaskState` must have at least one successful grounding step.

**Relationships**
- Belongs to one `TutorTaskState`.
- May reference deterministic service outputs indirectly via snapshots.

### 3. `TutorPersonaPromptRef`

Tracks which versioned prompt artifacts were used.

**Fields**
- `prompt_ref_id`: unique identifier
- `task_type`: `progress_report` | `worksheet_review` | `next_step_planning`
- `persona_path`: prompt file path for the shared persona block
- `task_path`: prompt file path for the task-specific block
- `version`: semantic or file-version label
- `language`: expected output language, normally `el`

**Validation rules**
- Both paths must resolve to versioned files under `app/prompts/`.
- `version` must be stable and match the prompt file naming strategy.
- Task prompts must require JSON output when the model is used.

**Relationships**
- Referenced by `TutorTaskState`.

### 4. `TutorOutcome`

Represents the final result returned to CLI/web callers.

**Fields**
- `task_id`: originating run identifier
- `summary_el`: optional Greek narrative
- `suggestions`: ordered list of advisory suggestions
- `deterministic_metrics`: exact code-owned numbers and facts
- `narrative_status`: `generated` | `degraded` | `not_requested`
- `error_code`: optional degraded/failed code
- `trace_summary`: compact audit-friendly metadata

**Validation rules**
- Numeric fields inside `deterministic_metrics` must come from deterministic services only.
- Suggestions must be advisory and parent-overridable.
- Narrative absence must always be explicit through `narrative_status`.

**Relationships**
- Derived from one `TutorTaskState`.

## State Transitions

### Tutor task lifecycle

1. `initialized` — task is created with task type and child context.
2. `grounding` — deterministic facts are collected from domain/service tools.
3. `reasoning` — the LLM is asked to produce grounded Greek narrative/suggestions.
4. `validating` — schema, safety, and deterministic consistency checks run.
5. `completed` — output is valid and ready to render.
6. `degraded` — model output failed but deterministic facts were still returned.
7. `failed` — a non-recoverable tool/graph error prevented completion.

## Persistence Notes

- The feature may add `agent_runs` and `agent_step_runs` tables or equivalent append-only
  records in `app/persistence/database.py`.
- Existing worksheet/submission/score tables remain unchanged.
- Traces should be compact and structured so they are reviewable without exposing raw
  sensitive data unnecessarily.


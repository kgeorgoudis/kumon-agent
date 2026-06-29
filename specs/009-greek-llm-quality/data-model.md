# Data Model: Improve Greek LLM Response Quality

**Feature**: 009-greek-llm-quality  
**Date**: 2026-06-29

---

## Overview

This feature introduces no new database entities and no schema migrations.
All changes are in the prompt layer (`app/prompts/v2/`) and the agent
orchestration layer (`app/agents/`). The existing `ProgressReport`,
`TutorTaskState`, and `TutorOutcome` domain models are reused without
modification, with one addition: a new error code constant in the
`narrative_status` / `llm_error_code` vocabulary.

---

## Existing Entities Affected

### `ProgressReport` (app/domain/models.py)

No field changes. The existing fields are sufficient:

| Field | Type | Role in this feature |
|-------|------|---------------------|
| `summary_el` | `str \| None` | Receives the improved Greek narrative |
| `narrative_status` | `str` | `"generated"` / `"degraded"` / `"not_requested"` |
| `llm_error_code` | `str \| None` | Extended with one new value (see below) |
| `prompt_version` | `str` | Will now reflect `"v2/progress_summary"` |
| `suggestions` | `list[ProgressSuggestion]` | Unchanged |

### `TutorTaskState` / `TutorOutcome` (app/domain/models.py)

No field changes. `error_code` already carries the error vocabulary.

---

## Error Code Vocabulary Extension

The `llm_error_code` / `error_code` string field is extended with one new value:

| Code | Meaning | Trigger |
|------|---------|---------|
| `ERR_LLM_EMPTY_SUMMARY` | LLM returned an empty or whitespace-only `summary_el` | New check in `_validation_node` |
| `ERR_LLM_WRONG_LANGUAGE` | `summary_el` contains English-language text | New heuristic check in `_validation_node` |

Existing codes remain unchanged:

| Code | Meaning |
|------|---------|
| `ERR_LLM_UNAVAILABLE` | Network / connection failure |
| `ERR_LLM_TRUNCATED` | Response cut off (`finish_reason == "length"`) |
| `ERR_LLM_INVALID_JSON` | Cannot parse JSON from response |
| `ERR_LLM_CONFLICTING_FACTS` | `summary_el` contains raw digit strings |
| `ERR_LLM_MISSING_SUMMARY` | Worksheet review `review_summary_el` was empty |
| `ERR_LLM_NO_SUGGESTIONS` | Next-step planning returned no suggestions |
| `ERR_NO_DATA` | No worksheets available for progress report |

---

## Configuration Extension

One new config entry in `app/config.py`:

| Variable | Env Override | Default | Purpose |
|----------|-------------|---------|---------|
| `PROMPT_VERSION` | `KUMON_PROMPT_VERSION` | `"v2"` | Selects the prompts sub-directory; setting to `"v1"` reverts to previous prompts |

---

## Prompt Artefacts (not persisted, but versioned)

| File | Version | Change |
|------|---------|--------|
| `app/prompts/v1/kumon_tutor_persona.md` | v1 | **Unchanged** |
| `app/prompts/v1/progress_summary.md` | v1 | **Unchanged** |
| `app/prompts/v2/kumon_tutor_persona.md` | v2 | Tighter constraints, explicit Greek-only rule |
| `app/prompts/v2/progress_summary.md` | v2 | Tighter task block + one concrete few-shot example |

---

## State Transition: No Change

The LangGraph `ProgressGraphState` and the step status transitions
(`initialized → grounding → reasoning → validating → completed/degraded`) are
unchanged. The new error codes slot into the existing `degraded` exit path
without any new edges.


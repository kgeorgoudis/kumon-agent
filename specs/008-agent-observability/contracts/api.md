# API Contract: Agent Observability and Traceability

**Feature**: Agent Observability and Traceability (`008-agent-observability`)  
**Interface**: FastAPI HTTP API  
**Date**: 2026-06-27  
**Base path**: `/api/v1/traces`

---

## Overview

Read-only trace retrieval endpoints for inspecting tutor task runs and step timelines. All endpoints delegate to the shared `TraceService` (Constitutional Principle IX: Shared Domain Logic). No writes occur through the API; traces are emitted from the agent graph layer only.

---

## Endpoints

### `GET /api/v1/traces`

List tutor task run summaries with optional filtering.

**Request parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | (all) | Filter by run status. Valid: `INITIALIZED`, `GROUNDING`, `REASONING`, `VALIDATING`, `COMPLETED`, `DEGRADED`, `FAILED` |
| `task_type` | string | No | (all) | Filter by task type. Valid: `PROGRESS_REPORT`, `WORKSHEET_REVIEW`, `NEXT_STEP_PLANNING` |
| `hours` | integer | No | `24` | Return runs created within the last N hours |
| `limit` | integer | No | `50` | Max results to return (1–500) |
| `offset` | integer | No | `0` | Pagination offset |

**Example request**:
```
GET /api/v1/traces?status=DEGRADED&hours=6&limit=20
```

**Response 200**:
```json
{
  "runs": [
    {
      "task_id": "abc123-def456-ghi789",
      "task_type": "PROGRESS_REPORT",
      "status": "DEGRADED",
      "prompt_version": "v1/progress_summary",
      "error_code": "LLM_TIMEOUT",
      "created_at": "2026-06-27T14:32:10Z",
      "updated_at": "2026-06-27T14:32:41Z",
      "duration_seconds": 31.2
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

**Response 400** (invalid parameter):
```json
{
  "detail": "Invalid status value: 'UNKNOWN'. Valid values: INITIALIZED, GROUNDING, REASONING, VALIDATING, COMPLETED, DEGRADED, FAILED"
}
```

**Response 503** (observability storage unavailable):
```json
{
  "detail": "Trace storage temporarily unavailable. Core tutor services remain operational."
}
```

---

### `GET /api/v1/traces/{task_id}`

Get full details for a single tutor task run, including step timeline.

**Path parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (UUID4) | Yes | The task run identifier |

**Query parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `detail` | string | No | `summary` | Level of detail: `summary` (metrics only) or `full` (includes sanitized input/output snapshots) |

**Example request**:
```
GET /api/v1/traces/abc123-def456-ghi789?detail=full
```

**Response 200 (summary)**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "task_type": "PROGRESS_REPORT",
  "status": "COMPLETED",
  "prompt_version": "v1/progress_summary",
  "error_code": null,
  "created_at": "2026-06-27T14:32:10Z",
  "updated_at": "2026-06-27T14:32:13Z",
  "duration_seconds": 2.34,
  "deterministic_context": {
    "skill_id": "multiplication_2_5",
    "accuracy_threshold": 80,
    "trend_window_days": 30
  },
  "output_summary": {
    "narrative_status": "generated",
    "recommendations_count": 2,
    "validation_status": "trusted"
  },
  "steps": [
    {
      "step_name": "ground_context",
      "status": "SUCCEEDED",
      "started_at": "2026-06-27T14:32:10Z",
      "finished_at": "2026-06-27T14:32:10.230Z",
      "error_code": null
    },
    {
      "step_name": "invoke_llm",
      "status": "SUCCEEDED",
      "started_at": "2026-06-27T14:32:10.230Z",
      "finished_at": "2026-06-27T14:32:12.185Z",
      "error_code": null
    },
    {
      "step_name": "validate_output",
      "status": "SUCCEEDED",
      "started_at": "2026-06-27T14:32:12.185Z",
      "finished_at": "2026-06-27T14:32:12.345Z",
      "error_code": null
    }
  ]
}
```

**Response 200 (detail=full)** — same as above, with `input_snapshot` and `output_snapshot` added to each step:
```json
{
  "steps": [
    {
      "step_name": "invoke_llm",
      "status": "SUCCEEDED",
      "input_snapshot": {
        "prompt_version": "v1/progress_summary",
        "model": "Qwen3-8B-MLX-4bit",
        "temperature": 0.2,
        "worksheet_history_count": 5
      },
      "output_snapshot": {
        "confidence_score": 0.92,
        "recommendation_types": ["advance", "focus_area"]
      }
    }
  ]
}
```

**Response 404** (run not found):
```json
{
  "detail": "Run not found: abc123-def456-ghi789"
}
```

**Response 422** (invalid UUID):
```json
{
  "detail": "Invalid task_id format. Expected UUID4."
}
```

---

### `GET /api/v1/traces/{task_id}/steps`

List all step traces for a single tutor task run in chronological order.

**Path parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (UUID4) | Yes | The task run identifier |

**Example request**:
```
GET /api/v1/traces/abc123-def456-ghi789/steps
```

**Response 200**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "steps": [
    {
      "step_id": "step-001-uuid",
      "step_name": "ground_context",
      "status": "SUCCEEDED",
      "error_code": null,
      "started_at": "2026-06-27T14:32:10.000Z",
      "finished_at": "2026-06-27T14:32:10.230Z",
      "duration_ms": 230
    },
    {
      "step_id": "step-002-uuid",
      "step_name": "invoke_llm",
      "status": "SUCCEEDED",
      "error_code": null,
      "started_at": "2026-06-27T14:32:10.230Z",
      "finished_at": "2026-06-27T14:32:12.185Z",
      "duration_ms": 1955
    }
  ],
  "total_steps": 3
}
```

**Response 404** (run not found):
```json
{
  "detail": "Run not found: abc123-def456-ghi789"
}
```

---

## Error Codes Reference

Trace-level error codes recorded in `error_code` field:

| Code | Description |
|------|-------------|
| `LLM_UNAVAILABLE` | LLM endpoint could not be reached |
| `LLM_TIMEOUT` | LLM response exceeded timeout |
| `LLM_INVALID_RESPONSE` | LLM returned malformed JSON or unexpected structure |
| `VALIDATION_FAILED` | Output validation failed; deterministic fallback applied |
| `TOOL_ERROR` | A deterministic tool (e.g., progress computation) raised an exception |
| `STORAGE_ERROR` | Trace persistence encountered a storage failure |

---

## HTTP Response Status Codes

| Status | Meaning |
|--------|---------|
| `200 OK` | Request succeeded with results (even if empty array) |
| `400 Bad Request` | Invalid parameter value (e.g., unknown status string) |
| `404 Not Found` | `task_id` not found in trace storage |
| `422 Unprocessable Entity` | Malformed path/query parameter (e.g., invalid UUID) |
| `503 Service Unavailable` | Trace storage temporarily unavailable (core services unaffected) |

---

## Testing Scenarios

**SC1 (Happy Path)**: `GET /api/v1/traces` returns list of completed runs

**SC2 (Filter)**: `GET /api/v1/traces?status=DEGRADED` returns only degraded runs

**SC3 (Empty)**: `GET /api/v1/traces?status=FAILED&hours=1` with no failures → `{"runs": [], "total": 0, ...}`

**SC4 (Show Run)**: `GET /api/v1/traces/{task_id}` → full run summary + step timeline

**SC5 (Not Found)**: `GET /api/v1/traces/nonexistent-id` → `404`

**SC6 (Steps)**: `GET /api/v1/traces/{task_id}/steps` → ordered step list with durations

**SC7 (Storage Down)**: DB unavailable → `503` with meaningful message; core `/progress` still functional


# Research: Agent Observability and Traceability

**Feature**: Agent Observability and Traceability (`008-agent-observability`)  
**Date**: 2026-06-27  
**Status**: Research Phase Complete

---

## Research Questions

### Q1: Best Practices for LangGraph Tracing and Event Capture

**Decision**: Use LangGraph's built-in tracing hooks + custom observability service layer

**Rationale**:
- LangGraph provides `debug=True` and callback handlers for step-level events (`on_start`, `on_stream`, `on_end`)
- Callback handlers are the idiomatic way to capture execution lifecycle without modifying graph code
- However, LangGraph's built-in tracing is primarily for debugging; we need a production observability layer with persistence

**Recommendation**:
- Use LangGraph's callback interface to hook into node execution
- Implement custom `ObservabilityCallback` handler that collects run/step events
- Emit events to observability service for persistence and retrieval
- This keeps observability decoupled from core agent logic while maintaining tight integration

**Alternative rejected**: Direct instrumentation of graph nodes (couples observability to agent logic; harder to test in isolation)

---

### Q2: SQLite Schema for Run and Step Traces

**Decision**: Two-table append-only schema with foreign key linkage

**Rationale**:
- Run records are immutable once created (one per task execution)
- Step records are append-only lifecycle events within a run
- Indexed on run_id, status, task_type, created_at for fast retrieval and filtering
- Uses existing Pydantic models (TutorTaskState, TutorStepTrace) from `app/domain/models.py`

**Schema outline**:
```sql
CREATE TABLE tutor_task_state (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    child_id TEXT,
    status TEXT NOT NULL,
    prompt_version TEXT,
    deterministic_context JSON,
    error_code TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at)
);

CREATE TABLE tutor_step_trace (
    step_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_snapshot JSON,
    output_snapshot JSON,
    error_code TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tutor_task_state(task_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
);
```

**Rationale for JSON columns**:
- Deterministic context (e.g., worksheet generation parameters) is semi-structured and may vary by task type
- Output snapshots are sanitized summaries, not full payloads
- JSON allows schema evolution without migrations

**Alternative rejected**: Fully normalized schema (would require many columns for optional fields; JSON is more flexible for observability)

---

### Q3: Error Code Standardization for Degradation Paths

**Decision**: Adopt pattern-based error codes with fallback metadata

**Rationale**:
- Error codes enable operators to quickly classify failure modes (e.g., `LLM_TIMEOUT`, `STORAGE_ERROR`, `VALIDATION_FAILED`)
- Fallback path is recorded separately (e.g., `fallback_to_deterministic=true`) so operators know what was returned to user
- Codes are machine-readable and can be indexed/filtered

**Error code taxonomy**:
- `LLM_*`: LLM endpoint unavailable, timeout, invalid response
- `STORAGE_*`: Database write error, persistence layer failure
- `VALIDATION_*`: LLM output validation failed
- `TOOL_*`: Tool execution (worksheet generation, progress computation) failed
- `CONFIG_*`: Invalid configuration or runtime state

**Example fallback record**:
```json
{
  "task_id": "...",
  "error_code": "LLM_TIMEOUT",
  "fallback_to_deterministic": true,
  "fallback_reason": "LLM did not respond within 30s; returned deterministic progress report",
  "fallback_metadata": {"timeout_ms": 30000}
}
```

**Alternative rejected**: Unstructured error messages (hard to aggregate and analyze for support)

---

### Q4: Sanitization Patterns for PII and Secrets

**Decision**: Define sanitization rules at trace emission time; store only necessary summaries

**Rationale**:
- LLM may generate text containing child name, personal context, or intermediate reasoning
- SQLite is local but we should not rely solely on filesystem permissions
- Constitution XII explicitly requires no raw secrets or unnecessary child PII in traces

**Sanitization rules**:
1. **Deterministic context**: Include only task parameters (e.g., `skill_id`, `exercise_count`), not child name
2. **LLM input prompts**: Store only version hash, not full prompt text
3. **LLM output**: Store sanitized summary (e.g., `accuracy_trend=improving, num_recommendations=2`), not full narrative
4. **Tool outputs**: Store only aggregate metrics (e.g., `worksheet_count=15`), not individual exercise details

**Implementation**:
- Define `SanitizationPolicy` enum (DETERMINISTIC_ONLY, SUMMARY_ONLY, FULL)
- Apply policy at `ObservabilityService.emit_step()` time
- Tests verify that child name, email, raw LLM text are not present in storage

**Alternative rejected**: Store full payloads and sanitize on retrieval (higher storage cost; risk of accidental exposure if retrieval path bypassed)

---

### Q5: Operator-Facing Retrieval Surfaces

**Decision**: CLI commands + HTTP API endpoints, both powered by shared TraceService

**Rationale**:
- Constitution IX (Shared Domain Logic) requires both CLI and web to use same retrieval layer
- Operators may use CLI for quick diagnosis or web UI for historical inspection
- Shared service layer prevents logic duplication

**Retrieval surfaces**:

**CLI commands** (typer):
```
kumon traces list [--status COMPLETED|DEGRADED|FAILED] [--type PROGRESS_REPORT] [--hours 24]
kumon traces show <task_id>
kumon traces filter --type WORKSHEET_REVIEW --status DEGRADED
```

**HTTP API endpoints** (FastAPI):
```
GET /api/v1/traces?status=DEGRADED&task_type=PROGRESS_REPORT&hours=24
GET /api/v1/traces/{task_id}
GET /api/v1/traces/{task_id}/steps
```

**Both surfaces**:
- Return trace summaries by default (for performance)
- Accept `?detail=full` to include input/output snapshots
- Filter by status, task type, time window
- Sort by creation time (newest first)

---

### Q6: Graceful Degradation When Observability Unavailable

**Decision**: Observability failures MUST NOT block tutor task execution; emit warning to user

**Rationale**:
- Constitution XII requires graceful degradation
- Tutor workflows are more important than observability records
- If SQLite write fails, system should complete task and alert operator, not abort

**Implementation**:
- `ObservabilityService.emit_run()` and `emit_step()` have try/except with fallback
- On storage error, log warning and continue (no exception propagation to agent graph)
- Return a boolean flag indicating success/failure to caller
- If traces unavailable, CLI retrieval shows `[traces unavailable for this run]` instead of crashing

**Testing requirement**: Test one successful run with observability working + one with observability storage disabled; verify both produce valid tutor output

**Alternative rejected**: Fail fast on observability error (would interrupt user experience; violates Constitution XII)

---

## Decisions Summary

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Tracing approach** | LangGraph callbacks + custom service layer | Decoupled, idiomatic, testable |
| **Schema** | Two-table append-only with JSON | Flexible, evolutionary, performant |
| **Error codes** | Pattern-based taxonomy (LLM_*, STORAGE_*) | Machine-readable, queryable, standard |
| **Sanitization** | Apply policies at emission time | Secure by default, consistent |
| **Retrieval** | Shared CLI + HTTP service layer | Constitution IX compliance |
| **Degradation** | Graceful (warn, continue) | Constitution XII, user experience |

---

## Next Steps

- **Phase 1 Design**: Define trace entity models (extends TutorTaskState/TutorStepTrace), create storage layer, design service API
- **Phase 1 Design**: Finalize CLI and HTTP API contracts
- **Phase 1 Quickstart**: Document how to enable tracing, query runs, interpret traces for operators


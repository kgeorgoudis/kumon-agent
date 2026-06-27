# Quickstart: Agent Observability and Traceability

**Feature**: Agent Observability and Traceability (`008-agent-observability`)  
**Date**: 2026-06-27

---

## What Is This?

Every time the app runs a tutor task (progress report, worksheet review, next-step planning), it records a **trace** in the local database. Traces let you:

- See what steps ran, in what order, and how long each took
- Diagnose degraded or failed runs with machine-readable error codes
- Confirm the LLM fallback worked correctly when the model was unavailable
- Audit what deterministic data was passed to the tutor before reasoning

---

## Prerequisites

- Project installed (`uv sync --dev`)
- At least one tutor task has been run (e.g., `kumon progress --child "Ελένη"`)

---

## 1. Run a Tutor Task (to Generate Traces)

```bash
# Generate a progress report — this creates a run trace
uv run kumon progress

# With a named child profile
uv run kumon progress --child "Ελένη"

# Without LLM (fast, deterministic-only, no trace for LLM steps)
uv run kumon progress --no-llm
```

---

## 2. List Recent Runs

```bash
# Show all runs from the last 24 hours
uv run kumon traces list

# Show only degraded or failed runs
uv run kumon traces list --status DEGRADED
uv run kumon traces list --status FAILED

# Show only progress report tasks
uv run kumon traces list --type PROGRESS_REPORT

# Show runs from the last 6 hours only
uv run kumon traces list --hours 6

# Combine filters
uv run kumon traces list --status DEGRADED --type WORKSHEET_REVIEW --hours 12
```

**Example output**:
```
Task ID                               Type                Status     Created At            Error Code
────────────────────────────────────  ──────────────────  ─────────  ────────────────────  ──────────────
abc123-def456-ghi789                  PROGRESS_REPORT     COMPLETED  2026-06-27 14:32:10   —
jkl012-mno345-pqr678                  WORKSHEET_REVIEW    DEGRADED   2026-06-27 14:15:22   LLM_TIMEOUT
```

---

## 3. Inspect a Single Run

```bash
# Show run summary with step timeline
uv run kumon traces show abc123-def456-ghi789

# Show full detail including sanitized input/output snapshots
uv run kumon traces show abc123-def456-ghi789 --detail full
```

**Example output (summary)**:
```
────────────────────────────────────
Task ID:         abc123-def456-ghi789
Task Type:       PROGRESS_REPORT
Status:          COMPLETED
Prompt Version:  v1/progress_summary
Created:         2026-06-27 14:32:10
Duration:        2.34 s
Error Code:      (none)

Deterministic Context:
  skill_id: multiplication_2_5
  worksheet_count: 5
  avg_accuracy_pct: 82.5

Step Timeline:
  1. ground_context    ✅ SUCCEEDED     0.23 s
  2. invoke_llm        ✅ SUCCEEDED     1.96 s
  3. validate_output   ✅ SUCCEEDED     0.16 s

Output Summary:
  narrative_status: generated
  recommendations_count: 2
  validation_status: trusted
────────────────────────────────────
```

---

## 4. Diagnose a Degraded Run

When a run degrades (LLM unavailable, validation failed), the trace shows exactly why and what fallback was used.

```bash
# Find degraded runs
uv run kumon traces list --status DEGRADED

# Inspect the degraded run
uv run kumon traces show jkl012-mno345-pqr678
```

**Example degraded run output**:
```
────────────────────────────────────
Task ID:         jkl012-mno345-pqr678
Task Type:       WORKSHEET_REVIEW
Status:          DEGRADED ⚠️
Error Code:      LLM_TIMEOUT
Fallback Used:   Yes — deterministic review applied

Step Timeline:
  1. ground_context    ✅ SUCCEEDED      0.15 s
  2. invoke_llm        ❌ FAILED         30.05 s  (LLM_TIMEOUT)
  3. apply_fallback    ✅ SUCCEEDED       0.02 s
  4. validate_output   ✅ SUCCEEDED       0.08 s

Output Summary:
  narrative_status: degraded
  validation_status: fallback
────────────────────────────────────
```

---

## 5. Via HTTP API (when server is running)

Start the API server:

```bash
uv run uvicorn app.api:api --reload
```

Then query traces via HTTP:

```bash
# List recent runs
curl http://127.0.0.1:8000/api/v1/traces

# Filter by status
curl "http://127.0.0.1:8000/api/v1/traces?status=DEGRADED&hours=6"

# Inspect a specific run
curl http://127.0.0.1:8000/api/v1/traces/abc123-def456-ghi789

# Get step-level detail
curl http://127.0.0.1:8000/api/v1/traces/abc123-def456-ghi789/steps

# Full detail with snapshots
curl "http://127.0.0.1:8000/api/v1/traces/abc123-def456-ghi789?detail=full"
```

---

## 6. Understanding Error Codes

| Error Code | What It Means | What To Do |
|------------|---------------|------------|
| `LLM_UNAVAILABLE` | LLM server was offline | Start local LLM server: `mlx_lm.server --model Qwen3-8B-MLX-4bit` |
| `LLM_TIMEOUT` | LLM took too long | Check LLM server load; reduce `--exercises` count |
| `LLM_INVALID_RESPONSE` | LLM returned bad JSON | Check prompt version and model compatibility |
| `VALIDATION_FAILED` | Output failed quality checks | Review LLM output in run details with `--detail full` |
| `TOOL_ERROR` | A calculation step failed | Check for missing worksheet/submission data |
| `STORAGE_ERROR` | Trace couldn't be saved | Check disk space at `data/kumon.db` |

---

## 7. What Traces Do NOT Store

Traces are sanitized at write time. They **never** contain:

- Child's display name, age, or personal details
- Full LLM prompt or response text  
- Individual exercise answers
- API keys or secrets

Traces store only: skill IDs, aggregate metrics, step durations, error codes, and prompt version references.

---

## 8. Running Observability Tests

```bash
# Run all observability tests
uv run pytest app/tests/test_observability_service.py -v
uv run pytest app/tests/test_observability_agent_integration.py -v

# Run the full observability suite in one command
uv run pytest app/tests/test_observability_service.py app/tests/test_observability_agent_integration.py -v

# Run entire suite (should still be 100% green)
uv run pytest
```

---

## Architecture Reference

```
CLI: kumon traces list/show/filter
        ↓
API: GET /api/v1/traces[/{task_id}[/steps]]
        ↓
TraceService (app/observability/service.py)
        ↓
Database.list_agent_runs() / .get_agent_run() / .list_agent_step_runs()
        ↓
SQLite: agent_runs + agent_step_runs tables (data/kumon.db)
        ↑ (written by)
app/agents/traces.py — persist_step_start / persist_step_finish
        ↑ (called from)
app/agents/agent_graph.py — LangGraph node callbacks
```

---

## Troubleshooting

**No traces showing up**

```bash
# Confirm a tutor task has been run
uv run kumon progress

# Then check
uv run kumon traces list
```

**`[traces unavailable]` warning**

The trace storage had a write error (usually disk full or permissions). The tutor task still completed. Check `data/kumon.db` permissions and disk space.

**`404` on `kumon traces show <id>`**

The task ID doesn't exist (may be from a session before observability was added). Run `kumon traces list` to find current IDs.


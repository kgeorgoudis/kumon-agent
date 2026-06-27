# CLI Contract: Agent Observability and Traceability

**Feature**: Agent Observability and Traceability (`008-agent-observability`)  
**Interface**: Typer CLI (`kumon` command)  
**Date**: 2026-06-27

---

## Overview

The CLI exposes trace inspection commands under a new `traces` command group. Operators can list runs, inspect individual runs, and filter by status/type/time.

---

## Commands

### `kumon traces list`

**Purpose**: List recent tutor task runs with summaries.

**Syntax**:
```bash
kumon traces list [OPTIONS]
```

**Options**:
- `--status [INITIALIZED|GROUNDING|REASONING|VALIDATING|COMPLETED|DEGRADED|FAILED]` — Filter by run status (default: all)
- `--type [PROGRESS_REPORT|WORKSHEET_REVIEW|NEXT_STEP_PLANNING]` — Filter by task type (default: all)
- `--hours INT` — Show runs from last N hours (default: 24)
- `--limit INT` — Max results to return (default: 50, max: 500)
- `--sort [created_at|status]` — Sort order (default: created_at, newest first)

**Example usage**:
```bash
# List all recent runs
kumon traces list

# List degraded runs from the last 6 hours
kumon traces list --status DEGRADED --hours 6

# List all progress reports
kumon traces list --type PROGRESS_REPORT --limit 100
```

**Output format (table)**:
```
Task ID                              Type              Status     Created At           Error Code
───────────────────────────────────  ───────────────  ────────  ─────────────────────  ──────────────
abc123-def456-ghi789                 PROGRESS_REPORT  COMPLETED 2026-06-27T14:32:10Z  —
jkl012-mno345-pqr678                 WORKSHEET_REVIEW DEGRADED  2026-06-27T14:15:22Z  LLM_TIMEOUT
stu901-vwx234-yza567                 NEXT_STEP_PLAN…  FAILED    2026-06-27T13:45:01Z  VALIDATION_FAILED
```

**No traces scenario**:
```
No runs found matching the filter.
Try:
  kumon traces list --hours 48    # Expand time window
  kumon traces list --status FAILED  # Look for specific status
```

---

### `kumon traces show <task_id>`

**Purpose**: Inspect a single run with full details and step timeline.

**Syntax**:
```bash
kumon traces show <task_id> [OPTIONS]
```

**Arguments**:
- `<task_id>` (required) — Task ID (UUID format)

**Options**:
- `--detail [summary|full]` — Level of detail (default: summary; full includes input/output snapshots)

**Example usage**:
```bash
# Show summary of a run
kumon traces show abc123-def456-ghi789

# Show full details with step snapshots
kumon traces show abc123-def456-ghi789 --detail full
```

**Output format (summary)**:
```
Task ID:             abc123-def456-ghi789
Task Type:           PROGRESS_REPORT
Status:              COMPLETED
Prompt Version:      v1/progress_summary
Child ID:            child-123 (sanitized)
Created:             2026-06-27T14:32:10Z
Duration:            2.34 seconds
Error Code:          (none)

Deterministic Context:
  skill_id: multiplication_2_5
  accuracy_threshold: 80%
  trend_window_days: 30

Step Timeline:
  1. ground_context            SUCCEEDED     0.23s
  2. invoke_llm                SUCCEEDED     1.95s
  3. validate_output           SUCCEEDED     0.16s

Output Summary:
  narrative_status: generated
  recommendations_count: 2
  confidence: 0.92
```

**Output format (full, with detail=full)**:
```
[Same as summary, plus:]

Input Snapshots:
  Step 1 (ground_context):
    - worksheet_history_count: 5
    - avg_accuracy_pct: 82.5

  Step 2 (invoke_llm):
    - prompt_version: v1/progress_summary
    - model: Qwen3-8B-MLX-4bit
    - temperature: 0.7

Output Snapshots:
  Step 2 (invoke_llm):
    - confidence_score: 0.92
    - recommendation_types: [advance, focus_area]

  Step 3 (validate_output):
    - validation_passed: true
```

**Degraded run output**:
```
Task ID:             jkl012-mno345-pqr678
Task Type:           WORKSHEET_REVIEW
Status:              DEGRADED
Error Code:          LLM_TIMEOUT
Fallback Used:       true
Fallback Reason:     LLM did not respond within 30s; returned deterministic review summary

Step Timeline:
  1. ground_context    SUCCEEDED     0.15s
  2. invoke_llm        FAILED        30.05s (timeout)
  3. apply_fallback    SUCCEEDED     0.02s
  4. validate_output   SUCCEEDED     0.08s

Output Summary:
  review_type: deterministic_fallback
  error_msg_el: "Δεν ήταν δυνατή η σύνδεση με το μοντέλο. Εμφανίζεται αναφορά χωρίς σχόλια."
```

**Not found scenario**:
```
Error: Task not found (task_id: abc123-def456-ghi789)

Recent task IDs:
  kumon traces list --hours 1
```

---

### `kumon traces filter`

**Purpose**: Advanced filtering with complex queries (alternative to `list` for power users).

**Syntax**:
```bash
kumon traces filter [OPTIONS]
```

**Options**:
- `--status STATUS` — Run status (can be repeated for OR: `--status DEGRADED --status FAILED`)
- `--type TYPE` — Task type (can be repeated)
- `--hours INT` — Last N hours
- `--error-code CODE` — Exact error code match
- `--sort [created_at|status]`
- `--output [table|json]` — Output format (default: table)

**Example usage**:
```bash
# Show all degraded or failed runs from last 12 hours
kumon traces filter --status DEGRADED --status FAILED --hours 12

# Show runs with specific error codes
kumon traces filter --error-code LLM_TIMEOUT --error-code VALIDATION_FAILED

# Export as JSON for scripting
kumon traces filter --status COMPLETED --hours 24 --output json
```

**JSON output**:
```json
[
  {
    "task_id": "abc123-def456-ghi789",
    "task_type": "PROGRESS_REPORT",
    "status": "COMPLETED",
    "error_code": null,
    "created_at": "2026-06-27T14:32:10Z",
    "updated_at": "2026-06-27T14:32:13Z"
  }
]
```

---

## Error Handling

### Command Errors

**Invalid task_id format**:
```
Error: Invalid task ID format (expected UUID4): abc123-invalid
```

**Invalid status value**:
```
Error: Invalid status. Choose from: INITIALIZED, GROUNDING, REASONING, VALIDATING, COMPLETED, DEGRADED, FAILED
```

**Database error**:
```
Error: Could not retrieve traces (database error: connection timeout)
Tip: Check if SQLite database is accessible at data/kumon.db
```

### Graceful Degradation

**Observability unavailable**:
```
Warning: Trace data is currently unavailable.
Reason: SQLite database write error (disk space?)

Core tutor workflow unaffected. Retrying trace retrieval...
No runs found.
```

---

## Help and Discovery

### `kumon traces --help`

```
Usage: kumon traces [OPTIONS] COMMAND [ARGS]...

  Inspect tutor task execution traces.

  Traces show what happened during LLM-based tasks (progress reporting,
  worksheet review, next-step planning). Use traces to diagnose failures
  and understand how decisions were made.

Commands:
  list       List recent tutor task runs
  show       Show details of a single run
  filter     Advanced trace filtering
```

### `kumon traces list --help`

```
Usage: kumon traces list [OPTIONS]

  List recent tutor task runs with summaries.

Options:
  --status TEXT      Filter by run status (INITIALIZED|COMPLETED|DEGRADED|FAILED)
  --type TEXT        Filter by task type (PROGRESS_REPORT|WORKSHEET_REVIEW|NEXT_STEP_PLANNING)
  --hours INTEGER    Show runs from last N hours (default: 24)
  --limit INTEGER    Max results to return (default: 50, max: 500)
  --sort TEXT        Sort order (created_at|status, default: created_at)
  --help             Show this message and exit.

Examples:
  kumon traces list
  kumon traces list --status DEGRADED --hours 6
  kumon traces list --type PROGRESS_REPORT --limit 100
```

---

## Testing Scenarios

**SC1 (Happy Path)**: `kumon traces list` with completed runs in database
- Expected: Table of 1+ runs displayed, none with ERROR

**SC2 (Degraded Path)**: Run with error_code=LLM_TIMEOUT and status=DEGRADED
- Expected: `kumon traces list --status DEGRADED` shows the run with error code

**SC3 (No Data)**: Query with filters matching no runs
- Expected: "No runs found matching the filter" + suggestions

**SC4 (Not Found)**: `kumon traces show <invalid-id>`
- Expected: Error message + suggestions for finding valid IDs

**SC5 (Full Detail)**: `kumon traces show <task_id> --detail full`
- Expected: Step snapshots included in output

**SC6 (Graceful Degradation)**: Observability unavailable
- Expected: Warning message; tutor workflow still functional


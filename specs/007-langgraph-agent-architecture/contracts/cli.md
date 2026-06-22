# Contract: CLI

**Feature**: `007-langgraph-agent-architecture`
**Date**: 2026-06-22

## Purpose

Document the CLI surfaces that continue to rely on shared domain services and, for the
LLM-assisted tutor flows, the new LangGraph orchestration layer.

## Commands in scope

### `kumon progress`

**Purpose**: Render a child progress summary and next-step suggestions.

**Inputs**
- `--child/-c <name>`: optional child display name filter
- `--limit/-n <int>`: optional history depth
- `--no-llm`: deterministic-only path

**Output expectations**
- Deterministic metrics are always present.
- If the narrative path succeeds, the report includes a Greek summary and advisory
  suggestions.
- If the narrative path fails or the model is unavailable, the command still succeeds
  and clearly indicates degraded narrative status.
- The next-step suggestion remains advisory; the parent can override it in later flows.

**Failure modes**
- Unknown child: emit the existing empty-state behavior.
- No scored worksheets: emit the existing empty-state behavior.
- Model unavailable / invalid response / timeout: continue with deterministic-only output.

### `kumon submit`

**Purpose**: Collect manual answers, confirm them, and score the worksheet.

**Inputs**
- `<instance_id>`: worksheet instance identifier
- `--answers/-a <text>`: bulk answers
- `--time/-t <duration>`: optional duration
- `--resume`: resume a draft submission
- `--no-confirm`: skip the confirmation prompt in bulk mode

**Output expectations**
- Scoring remains deterministic and code-owned.
- The submission flow remains manual-first and does not depend on the model.
- Any future agent-assisted review step must not alter the scoring result.

### `kumon explain ...`, `kumon history`, `kumon pending`, `kumon generate`, `kumon profile ...`

**Purpose**: Existing commands remain unchanged in behavior.

**Output expectations**
- No breaking command changes are introduced by this feature.
- Existing help text and argument contracts stay compatible.

## CLI invariants

- CLI entry points stay thin and delegate to shared services or agent facades.
- Child/parent-facing text remains Greek-first.
- No command may require network access to succeed in its deterministic mode.


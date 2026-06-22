# Contract: API

**Feature**: `007-langgraph-agent-architecture`
**Date**: 2026-06-22

## Purpose

Document the HTTP surface that continues to share the same progress-reporting logic as
the CLI.

## Endpoint in scope

### `GET /progress`

**Purpose**: Render the HTML child progress summary page.

**Query parameters**
- `child` (optional): child display name
- `limit` (optional, default `20`): number of recent scored worksheets to include
- `llm` (optional, default `true`): enable or disable narrative generation

**Response**
- `200 OK` HTML page rendered from the shared progress report payload
- The page must show deterministic metrics even when `llm=false` or the model is down
- If narrative generation fails, the page must still render with degraded status text

**Behavioral contract**
- The API must call the same shared service layer used by the CLI.
- No arithmetic or progression computation is performed in the route handler.
- Greek-first presentation is preserved for parent-facing content.

## `GET /health`

**Purpose**: Lightweight liveness check.

**Response**
- `200 OK` with `{"status": "ok"}`

## API invariants

- The API remains secondary to the CLI and paper workflow.
- No endpoint in this feature may require the LLM to be available in order to serve
  deterministic responses.
- The API must not expose raw internal graph state unless explicitly added in a future
  versioned contract.


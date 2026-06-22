# Quickstart: LangGraph Agentic Architecture

**Feature**: `007-langgraph-agent-architecture`
**Date**: 2026-06-22

## Prerequisites

- Python 3.12+
- `uv`
- Local model endpoint available if you want narrative generation (optional for the
  deterministic-only path)

## Setup

```bash
cd /Users/K.Georgoudis/code/labs/kumon-agent
uv sync --dev
```

## Run the test suite

```bash
uv run pytest
```

Run the graph-focused regression subset:

```bash
uv run pytest app/tests/test_agent_state.py app/tests/test_agent_traces.py app/tests/test_agent_graph.py app/tests/test_agent_graph_fallback.py app/tests/test_agent_tools.py app/tests/test_prompt_registry.py -q
```

## Try the existing workflows

Generate a worksheet:

```bash
uv run kumon generate multiplication-2-5 --no-open
```

Create a child profile and view progress:

```bash
uv run kumon profile create "Ελένη" --age 10 --grade 4
uv run kumon progress --child "Ελένη" --no-llm
```

If the local model is running, try the narrative path as well:

```bash
uv run kumon progress --child "Ελένη"
```

Manually submit a worksheet and inspect the scoring flow:

```bash
uv run kumon pending --child "Ελένη"
uv run kumon submit <instance_id> --answers "1,2,3,4,5" --no-confirm
```

## What to verify after implementation

- Progress reporting still returns deterministic metrics when the model is off.
- LangGraph-driven tutor steps are visible in traces or audit records.
- CLI and web progress output stay consistent.
- Existing SQLite databases still open without migration issues.

## Helpful environment variables

```bash
export KUMON_LLM_BASE_URL="http://127.0.0.1:8000/v1"
export KUMON_LLM_MODEL="Qwen3-8B-MLX-4bit"
```

These remain optional for the agentic refactor, but they enable the narrative path.

## Latest validation snapshot

Verified locally on 2026-06-22:

```bash
uv run pytest -q
```

Result: `127 passed, 1 warning`


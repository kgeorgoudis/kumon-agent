# Implementation Plan: LangGraph Agentic Architecture

**Branch**: `007-langgraph-agent-architecture` | **Date**: 2026-06-22 | **Spec**: `specs/007-langgraph-agent-architecture/spec.md`

**Input**: Feature specification from `/specs/007-langgraph-agent-architecture/spec.md`

## Summary

Re-shape the project around a single agent orchestration layer for the existing tutor
LLM tasks — worksheet planning advice, worksheet review, and progress reporting —
while keeping arithmetic, scoring, and progression decisions deterministic and
code-owned. The implementation will introduce a LangGraph-based state graph with
explicit tool calls, versioned prompts, and graceful fallback paths so CLI and web
entry points continue to share the same domain services.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Typer, Rich, Jinja2, Pydantic, sqlite3 (stdlib),
OpenAI-compatible local client, LangGraph, langchain-openai, python-dotenv

**Storage**: SQLite (`data/kumon.db`) with append-only worksheet/submission/score
records plus new agent run/step trace records for inspectability

**Testing**: pytest with deterministic unit, integration, CLI, and web tests; model
calls mocked/stubbed for offline agent coverage

**Target Platform**: Local macOS/Linux/Windows environments; offline-first once
dependencies are installed

**Project Type**: Single Python application with shared `app/` package used by CLI,
FastAPI routes, domain services, and agent orchestration

**Performance Goals**: Preserve current worksheet generation and submission latency;
keep progress/report generation responsive under local inference; keep the full suite
green with no network dependency

**Constraints**: Arithmetic and scoring remain deterministic Python code; the agent
layer only reasons over deterministic facts; existing databases must continue to open
without destructive migration; child/parent-facing output stays Greek-first; all
LLM use must degrade safely when unavailable

**Scale/Scope**: Small-to-medium refactor across existing `app/` modules, prompt files,
tests, and SQLite schema helpers; no new product surface beyond the agentic foundation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Deterministic Before Agentic**: PASS — LangGraph is used only for tasks where
  stateful orchestration helps, while arithmetic/progression remain code-owned.
- **II. Arithmetic Truth From Code**: PASS — scoring and correctness stay in Python
  services and database snapshots.
- **III. Inspectable Progression**: PASS — the plan includes explicit agent run/step
  traces and machine-readable outputs.
- **IV. Parent Override Authority**: PASS — the parent remains the decision-maker; the
  agent returns suggestions, not automatic authority.
- **V. Paper Workflow First**: PASS — the generate → print → solve → manual submit →
  score loop is unchanged.
- **VI. Short and Incremental Assignments**: PASS — worksheet generation logic is not
  widened beyond the existing micro-skill model.
- **VII. Greek-First Content and UI**: PASS — prompts and outputs remain Greek-first
  for child/parent-facing content.
- **VIII. Local-First Architecture**: PASS — the agent targets the local endpoint and
  must degrade offline without cloud calls.
- **IX. Shared Domain Logic**: PASS — CLI and web/API continue to call the same service
  layer, with the agent consuming those services as tools.
- **X. In-App Documentation**: PASS — prompt/version docs and `explain` content remain
  versioned and accessible.
- **XI. Kumon Tutor Persona**: PASS — persona-driven reasoning is encoded in versioned
  prompts and grounded in deterministic facts.

## Project Structure

### Documentation (this feature)

```text
specs/007-langgraph-agent-architecture/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── cli.md
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - not created here)
```

### Source Code (repository root)

```text
app/
├── agents/
│   ├── __init__.py
│   ├── llm_client.py
│   ├── agent_graph.py        # LangGraph state graph / orchestration entry point
│   ├── state.py              # Typed agent state and run metadata
│   ├── tools.py              # Deterministic tool wrappers around services/domain
│   └── traces.py             # Optional run/step trace helpers
├── api/
│   └── __init__.py           # Thin HTTP layer over shared services
├── cli/
│   └── main.py               # CLI commands remain the user entry point
├── domain/
│   ├── models.py
│   ├── knowledge_base.py
│   └── math_engine.py
├── persistence/
│   └── database.py           # SQLite + new agent trace persistence helpers
├── prompts/
│   └── v1/
│       ├── README.md
│       ├── kumon_tutor_persona.md
│       ├── progress_summary.md
│       ├── worksheet_review.md
│       ├── next_step_planning.md
│       └── explain_mistake.md
├── services/
│   ├── progress_summary_service.py
│   ├── progression_service.py
│   ├── scoring_service.py
│   ├── submission_service.py
│   ├── tutor_planning_service.py
│   ├── worksheet_review_service.py
│   └── worksheet_generator.py
└── tests/
    ├── test_cli_*.py
    ├── test_database.py
    ├── test_progress_summary_service.py
    ├── test_progression_service.py
    ├── test_submission_service.py
    ├── test_web_progress.py
    └── test_*agent*.py        # new coverage for LangGraph state + fallback paths
```

**Structure Decision**: Keep the existing single-project layout and add a dedicated
agent orchestration subpackage under `app/agents/`. Existing domain and service modules
remain the source of truth; the new agent graph composes them as deterministic tools so
CLI and web/API entry points stay thin and shared.

## Complexity Tracking

No constitution violations require justification. The plan stays within the existing
architecture and adds the minimum new surface needed for LangGraph orchestration and
traceability.

# Implementation Plan: Agent Observability and Traceability

**Branch**: `008-agent-observability` | **Date**: 2026-06-27 | **Spec**: `specs/008-agent-observability/spec.md`

**Input**: Feature specification from `/specs/008-agent-observability/spec.md`

## Summary

Implement Constitutional Principle XII by building a structured observability layer that emits and persists agent task run and step traces with lifecycle status, error codes, deterministic context snapshots, and fallback metadata. This enables parent-facing operators and developers to inspect tutor task execution, diagnose degraded outcomes, and maintain audit compliance without blocking core tutor workflows when observability storage is unavailable. The implementation reuses existing LangGraph agent task state models and extends SQLite persistence with trace schema, adding an observability service layer and CLI/web retrieval surfaces for run inspection and filtering.

## Technical Context

**Language/Version**: Python 3.12 (existing requirement per constitution)

**Primary Dependencies**: 
- LangGraph (existing, used for tutor orchestration)
- SQLite3 (stdlib, existing default persistence)
- Pydantic (existing, used for domain models)
- Python structlog or built-in logging (structured trace emission)

**Storage**: SQLite (existing `data/kumon.db` already has `agent_runs` and `agent_step_runs` tables with `save_agent_run`, `get_agent_run`, `save_agent_step_run`, `list_agent_step_runs` methods; this feature adds `list_agent_runs` with filtering, plus status/task_type indexes for efficient querying)

**Testing**: pytest (existing; add agent trace coverage for success/degraded paths per Principle XII)

**Target Platform**: Linux/macOS/Windows offline environments (existing local-first constraint)

**Project Type**: Single Python application (existing `app/` package with dedicated `app/observability/` subpackage for trace logic)

**Performance Goals**: Trace writes <50ms p95, retrieval queries <200ms for standard filters (by status, task type, time window)

**Constraints**: 
- Observability failures MUST NOT block tutor task execution (degrade gracefully per Principle XII)
- All traces MUST remain local (no external logging, per Principle VIII)
- Traces MUST NOT contain raw secrets or unnecessary child PII (per Principle XII)
- System MUST operate fully offline once dependencies installed

**Scale/Scope**: 
- Core agent infrastructure is already partially in place: `app/agents/traces.py` provides `persist_step_start` / `persist_step_finish` / `list_task_traces`; `app/persistence/database.py` already has the `agent_runs` + `agent_step_runs` schema and CRUD methods; `app/domain/models.py` defines `TutorTaskState`, `TutorStepTrace`, `TutorTaskStatus`, `TutorStepStatus`
- **Remaining work**: add `list_agent_runs` retrieval/filtering to `Database`; add status/task_type indexes; build `app/observability/` service layer; add CLI `traces` command group; add HTTP API trace endpoints; add test coverage for success/degraded paths
- Scope limited to tutor orchestration runs (progress_summary, worksheet_review, next_step_planning tasks)
- Historical backfill out of scope; observability guarantees apply to new runs post-rollout

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Deterministic Before Agentic**: PASS — Observability is metadata/traceability infrastructure; it does not introduce non-deterministic computation. LLM task execution remains under LangGraph orchestration; observability only records what was computed and why.
- **II. Arithmetic Truth From Code**: PASS — Observability does not modify arithmetic pathways. Traces record deterministic context and outputs but never compute or validate answers.
- **III. Inspectable Progression Decisions**: PASS — Observability directly supports this principle by recording progression task runs with decision rationale, context snapshots, and error codes.
- **IV. Parent Override Authority**: PASS — Observability infrastructure includes audit trail capability for overrides; trace persistence enables operator review of parent-initiated changes.
- **V. Paper Workflow First**: PASS — Observability is non-intrusive to core worksheet generate → print → solve → submit → score loop. Traces are background metadata.
- **VI. Short and Incremental Assignments**: PASS — Observability does not affect worksheet generation or micro-skill progression logic.
- **VII. Greek-First Content and UI**: PASS — Observability traces are internal/developer-facing. CLI and web trace retrieval surfaces can be localized to Greek for parent-facing operators.
- **VIII. Local-First Architecture**: PASS — All traces persisted to local SQLite; no cloud logging. System works fully offline. Trace storage failures do not disrupt tutor task execution.
- **IX. Shared Domain Logic**: PASS — Observability integrates with existing service layer; CLI and web both use same trace retrieval service (no duplication).
- **X. In-App Documentation**: PASS — No conflict. Observability adds optional trace visibility; CLI `--help` and web UI can document trace inspection commands.
- **XI. Kumon Tutor Persona**: PASS — Observability records tutor task execution but does not influence persona reasoning. Traces capture prompt version and task inputs/outputs for auditability.
- **XII. Agent Observability and Traceability**: **DIRECTLY IMPLEMENTS** — This feature is the primary implementation vehicle for Principle XII.

**Verdict**: No principle violations. Feature is fully compliant with constitution v1.2.0.

## Project Structure

### Documentation (this feature)

```text
specs/008-agent-observability/
├── plan.md                    # This file (/speckit.plan command output)
├── research.md                # Phase 0 output: trace schema best practices, LangGraph integration patterns
├── data-model.md              # Phase 1 output: trace entity definitions, retrieval filter contracts
├── quickstart.md              # Phase 1 output: how to enable traces, query runs, inspect step details
├── contracts/
│   ├── cli.md                 # CLI contract: trace inspection commands (list-runs, show-run, etc.)
│   └── api.md                 # HTTP API contract: trace retrieval endpoints
└── checklists/
    └── requirements.md        # Spec validation checklist
```

### Source Code (repository root)

```text
app/
├── observability/             # NEW: Observability service layer
│   ├── __init__.py
│   ├── service.py             # TraceService: list/filter runs, retrieve run+steps, sanitize
│   └── __pycache__/
├── agents/
│   ├── traces.py              # EXISTING: persist_step_start/finish, list_task_traces — NO CHANGES needed
│   ├── agent_graph.py         # EXISTING: already calls traces.py — NO CHANGES needed for emission
│   ├── state.py               # EXISTING: TutorTaskState, TutorStepTrace, enums — NO CHANGES
│   └── ...existing files...
├── persistence/
│   └── database.py            # EXTEND: add list_agent_runs(filter) + status/task_type indexes
├── cli/
│   └── main.py                # EXTEND: add `traces` command group (list, show, filter)
├── api/
│   └── __init__.py            # EXTEND: add GET /api/v1/traces, /api/v1/traces/{id}, /api/v1/traces/{id}/steps
└── tests/
    ├── test_observability_service.py          # NEW: list/filter runs, retrieve run+steps
    ├── test_observability_agent_integration.py # NEW: verify traces emitted on success + degraded paths
    └── ...existing files...
```

**Structure Decision**: The core trace emission infrastructure (`app/agents/traces.py`, `app/persistence/database.py` schema + CRUD, `app/domain/models.py` state models) already exists from the LangGraph architecture feature. This feature adds the **retrieval and inspection layer** on top: a `TraceService` in `app/observability/` for filtered run listing; CLI `traces` commands; HTTP API trace endpoints; and missing database filtering. No changes to the agent graph emission path are required.

## Complexity Tracking

> No Constitution Check violations; no complexity tracking required.

**Rationale**: This feature directly implements an existing constitutional principle (XII) and integrates with the existing LangGraph architecture without introducing new external dependencies or architectural layers.

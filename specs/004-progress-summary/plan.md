# Implementation Plan: Progress Summary

**Branch**: `004-progress-summary` | **Date**: 2026-06-18 | **Spec**: `specs/004-progress-summary/spec.md`

**Input**: Feature specification from `/specs/004-progress-summary/spec.md`

## Summary

Add a shared progress-report service that aggregates scored worksheet history deterministically, then optionally asks the local LLM to generate a Greek narrative and next-step suggestions grounded in those computed metrics. Expose the same report through a new CLI command and a simple server-rendered web page, with graceful fallback when the LLM is unavailable.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Typer, Rich, FastAPI, Jinja2, Pydantic, sqlite3 (stdlib), OpenAI SDK client, pytest

**Storage**: SQLite (`data/kumon.db`) via `app/persistence/database.py`

**Testing**: pytest (`app/tests/` for service, CLI, and web route coverage)

**Target Platform**: Local macOS/Linux/Windows environments (offline-first)

**Project Type**: Single-project Python application (`app/`) with shared services consumed by CLI and web

**Performance Goals**:
- Deterministic aggregation returns in <=2 seconds when LLM is unavailable (`SC-004`).
- Report generation completes in <=10 seconds excluding LLM latency (`SC-001`).

**Constraints**:
- LLM is used only for narrative/suggestions; all metrics and trend labels are deterministic (`FR-009`).
- Prompt must be versioned under `app/prompts/v1/` (`FR-010`).
- Parent-facing text defaults to Greek (`FR-004`, `FR-005`).
- Local-first behavior; no cloud dependency required (`Principle VIII`).

**Scale/Scope**:
- Single-household usage with low-to-moderate worksheet volume (1-5/day).
- v1 scope: one child report at a time, based on confirmed submissions and score snapshots.
- Includes CLI and simple web entrypoint with one shared service (`FR-006`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **I. Deterministic Before Agentic**: PASS - aggregation, trend classification, and skill stats are deterministic; LLM is optional narrative layer only.
- **II. Arithmetic Truth From Code**: PASS - no arithmetic/scoring delegated to LLM.
- **III. Inspectable Progression**: PASS - report includes machine-readable metrics and clear rationale fields for suggestions.
- **IV. Parent Override Authority**: PASS - feature is advisory/reporting only; no forced decisions.
- **V. Paper Workflow First**: PASS - summarizes outcomes of the existing paper submission loop.
- **VI. Short and Incremental Assignments**: PASS - suggestions can recommend incremental next steps without auto-applying changes.
- **VII. Greek-First Content/UI**: PASS - Greek output for CLI and web summary.
- **VIII. Local-First Architecture**: PASS - reads local SQLite and local LLM endpoint.
- **IX. Shared Domain Logic**: PASS - one progress service consumed by CLI + web.
- **X. In-App Documentation**: PASS - summary output explains progress and actionable guidance in-app.

### Post-Design Re-Check

- PASS - design keeps deterministic source-of-truth metrics separate from LLM text.
- PASS - no constitution violations identified; Complexity Tracking exceptions not needed.

## Phase 0: Research Plan

Research completed in `specs/004-progress-summary/research.md` with decisions for:
- CLI/Web interface shape and child selection behavior.
- Deterministic aggregation source and trend calculation method.
- Structured prompt/response schema for LLM narrative generation.
- Graceful degradation path when local LLM is unavailable.
- Prompt versioning and storage location.

## Phase 1: Design & Contracts

Design artifacts produced:
- `specs/004-progress-summary/data-model.md`
- `specs/004-progress-summary/contracts/cli.md`
- `specs/004-progress-summary/contracts/web.md`
- `specs/004-progress-summary/quickstart.md`

Agent context update:
- `.github/copilot-instructions.md` updated to reference `specs/004-progress-summary/plan.md` between `SPECKIT` markers.

## Project Structure

### Documentation (this feature)

```text
specs/004-progress-summary/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── web.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── services/
│   └── progress_summary_service.py      # new shared aggregation + LLM narrative service
├── persistence/
│   └── database.py                      # add report query helpers/projections
├── domain/
│   └── models.py                        # add progress report value objects
├── prompts/
│   └── v1/
│       └── progress_summary.md          # versioned prompt template
├── cli/
│   └── main.py                          # add `progress` command
├── web/
│   └── ...                              # add progress route/controller
├── templates/
│   └── progress_summary.html.j2         # new parent-facing web page
└── tests/
    ├── test_progress_summary_service.py # new deterministic + fallback tests
    ├── test_cli_progress.py             # new CLI contract tests
    └── test_web_progress.py             # new web route rendering tests
```

**Structure Decision**: Keep the existing single-project architecture and introduce one shared progress-summary service in `app/services/`. CLI and web adapters remain thin, calling the same deterministic aggregation and optional LLM narrative pipeline.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

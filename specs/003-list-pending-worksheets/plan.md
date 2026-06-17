# Implementation Plan: List Pending Worksheets

**Branch**: `003-list-pending-worksheets` | **Date**: 2026-06-17 | **Spec**: `specs/003-list-pending-worksheets/spec.md`

**Input**: Feature specification from `/specs/003-list-pending-worksheets/spec.md`

## Summary

Add a dedicated CLI recovery command, `kumon pending`, so a parent can list worksheets that are still submittable after restarting the terminal and losing IDs printed by `kumon generate`. The feature is implemented as deterministic read logic over existing SQLite entities (`worksheet_instances`, `manual_submissions`) and displays full worksheet IDs for copy-paste into `kumon submit`.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Typer, Rich, Pydantic, sqlite3 (stdlib), pytest

**Storage**: SQLite (`data/kumon.db`) via `app/persistence/database.py`

**Testing**: pytest (`app/tests/` CLI + persistence/service coverage)

**Target Platform**: Local macOS/Linux/Windows terminal environments

**Project Type**: Single-project Python application (`app/`) with CLI-first entrypoint

**Performance Goals**:
- Pending list query completes in <200ms for typical local dataset (1-500 worksheets).
- Parent can identify and copy target worksheet ID within 5 seconds (SC-001).

**Constraints**:
- Deterministic status derivation only (no LLM).
- Greek-first parent-facing CLI messages.
- Full `instance_id` must be displayed (no truncation).
- Draft/cancelled submissions must not suppress pending rows.

**Scale/Scope**:
- Single-household local usage.
- Typical volume: 1-5 worksheets/day.
- Feature scope is CLI interface + shared persistence/service read model only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **I. Deterministic Before Agentic**: PASS - pending state is derived from SQLite statuses; no agentic components.
- **II. Arithmetic Truth From Code**: PASS - feature does not alter arithmetic/scoring logic.
- **III. Inspectable Progression**: PASS - command surfaces inspectable worksheet/submission state linkage.
- **IV. Parent Override Authority**: PASS - parent can still choose any listed worksheet and submit/resume explicitly.
- **V. Paper Workflow First**: PASS - supports paper loop recovery after terminal/session restart.
- **VI. Short and Incremental Assignments**: PASS - no change to worksheet length/progression policies.
- **VII. Greek-First Content/UI**: PASS - CLI output/messages remain Greek-first.
- **VIII. Local-First Architecture**: PASS - local SQLite query only.
- **IX. Shared Domain Logic**: PASS - pending query resides in persistence/service layer used by CLI.
- **X. In-App Documentation**: PASS - command help text documents usage in CLI.

### Post-Design Re-Check

- PASS - design introduces only deterministic read-model additions and CLI rendering.
- PASS - no constitution violations; Complexity Tracking exemptions not needed.

## Phase 0: Research Plan

Research completed in `specs/003-list-pending-worksheets/research.md` with decisions for:
- Command shape (`kumon pending`) and role separation from `history`.
- Pending-state definition (`NOT EXISTS confirmed submission`).
- Persistence query strategy and draft indicator projection.
- Child-filter behavior consistent with existing `_resolve_child` flow.
- Full-ID display rules for copy-paste workflow.

## Phase 1: Design & Contracts

Design artifacts produced:
- `specs/003-list-pending-worksheets/data-model.md`
- `specs/003-list-pending-worksheets/contracts/cli.md`
- `specs/003-list-pending-worksheets/quickstart.md`

Agent context update:
- `.github/copilot-instructions.md` updated to reference `specs/003-list-pending-worksheets/plan.md` between `SPECKIT` markers.

## Project Structure

### Documentation (this feature)

```text
specs/003-list-pending-worksheets/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── cli/
│   └── main.py                        # add `pending` command
├── services/
│   └── submission_service.py          # optional read-model helper (if needed)
├── persistence/
│   └── database.py                    # add pending worksheet query/projection
└── tests/
    ├── test_cli_pending.py            # new
    ├── test_database.py               # extend DB query tests
    └── test_submission_service.py     # extend pending semantics tests (if service helper added)
```

**Structure Decision**: Keep the existing single-project Python architecture. Implement pending-list read logic in persistence (and lightweight service helper only if needed), then expose via a new CLI command in `app/cli/main.py`, with tests in `app/tests/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

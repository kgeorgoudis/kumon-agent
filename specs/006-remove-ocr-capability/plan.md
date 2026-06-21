# Implementation Plan: Remove OCR Capability

**Branch**: `main` | **Date**: 2026-06-21 | **Spec**: `specs/006-remove-ocr-capability/spec.md`

**Input**: Feature specification from `/specs/006-remove-ocr-capability/spec.md`

## Summary

Remove OCR ingestion, OCR review, and OCR rescoring from the codebase so manual submission via `kumon submit` is the only worksheet submission path. Keep deterministic scoring and progress behavior intact, preserve backward-compatible SQLite schema where needed, and eliminate unused OCR dependencies/tests to reduce maintenance risk.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Typer, Rich, Jinja2, Pydantic, sqlite3 (stdlib), OpenAI client (local LLM narrative)

**Storage**: SQLite (`data/kumon.db`) via `app/persistence/database.py`; manual submissions and score snapshots remain primary persisted workflow

**Testing**: pytest (`app/tests/`) including CLI, persistence, scoring, progression, and web progress tests

**Target Platform**: Local macOS/Linux/Windows with offline-first operation

**Project Type**: Single-project Python app (`app/`) with shared domain/services used by CLI and web API

**Performance Goals**:
- Preserve current manual submission latency and deterministic scoring behavior.
- Keep `uv run pytest` green after OCR module removal.
- Keep CLI startup and command execution free of import errors.

**Constraints**:
- Deterministic scoring/progression must remain code-driven (Constitution I-II).
- Manual submission workflow must remain primary and unchanged for parents.
- Existing SQLite files must continue to open without destructive migration.
- OCR endpoints/modules must be fully removed from active code paths.

**Scale/Scope**:
- Repository-wide cleanup touching domain, services, persistence, API, config, tests, and dependency manifest.
- No new features; this is a subtractive refactor and consistency cleanup.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **I. Deterministic Before Agentic**: PASS - removal of OCR narrows non-deterministic surface area.
- **II. Arithmetic Truth From Code**: PASS - manual scoring remains deterministic Python logic.
- **III. Inspectable Progression**: PASS - score snapshots and progress reporting remain auditable.
- **IV. Parent Override Authority**: PASS - parent manual entry/review path remains intact.
- **V. Paper Workflow First**: PASS - print -> solve -> manual submit loop remains central.
- **VI. Short and Incremental Assignments**: PASS - worksheet generation logic unchanged.
- **VII. Greek-First Content and UI**: PASS - child/parent-facing wording remains Greek-first.
- **VIII. Local-First Architecture**: PASS - no cloud dependency introduced.
- **IX. Shared Domain Logic**: PASS - cleanup keeps shared service/domain architecture.
- **X. In-App Documentation**: PASS - documentation adjusted to manual-only workflow.
- **XI. Kumon Tutor Persona**: PASS - LLM remains optional for narrative only.

### Post-Design Re-Check

- PASS - design removes dead OCR modules without adding duplicate logic paths.
- PASS - persistence changes retain backward compatibility while simplifying runtime behavior.
- PASS - contracts/docs align to manual-only workflow and remove OCR ambiguity.
- PASS - no constitution violations identified; no exceptions required.

## Phase 0: Research Plan

Research findings are documented in `specs/006-remove-ocr-capability/research.md` and cover:
- Safe removal strategy for OCR modules while preserving manual scoring.
- Backward-compatible persistence handling for legacy OCR tables/columns.
- API/CLI contract impact of removing OCR endpoints and commands.
- Dependency cleanup strategy (remove OCR-only libs, keep narrative LLM stack).

## Phase 1: Design & Contracts

Design artifacts produced:
- `specs/006-remove-ocr-capability/data-model.md`
- `specs/006-remove-ocr-capability/contracts/cli.md`
- `specs/006-remove-ocr-capability/contracts/api.md`
- `specs/006-remove-ocr-capability/quickstart.md`

Agent context update:
- `.github/copilot-instructions.md` updated to reference `specs/006-remove-ocr-capability/plan.md`.

## Project Structure

### Documentation (this feature)

```text
specs/006-remove-ocr-capability/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   └── cli.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── domain/
│   ├── models.py                  # remove OCR entities, keep manual-submission entities
│   └── knowledge_base.py          # update loop description to manual-only submission
├── services/
│   ├── scoring_service.py         # remove OCR rescoring path
│   └── submission_service.py      # unchanged primary submission path
├── persistence/
│   └── database.py                # remove OCR methods, keep compatibility DDL/migration
├── agents/
│   ├── __init__.py                # remove OCR classification mention
│   └── llm_client.py              # remove OCR fallback client/probe helpers
├── api/
│   └── __init__.py                # remove /ocr endpoints, keep health/progress
├── cli/
│   └── main.py                    # documentation wording update only
└── tests/
    ├── test_database.py           # remove OCR-specific tests
    └── ...                        # remaining manual workflow tests unchanged

pyproject.toml                     # remove OCR-only dependencies
```

**Structure Decision**: Keep the existing single-project architecture and perform a subtractive cleanup across existing modules. Do not introduce replacement abstractions; rely on the existing manual submission/scoring path already shared across CLI and web reporting.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

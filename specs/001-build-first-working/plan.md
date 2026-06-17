# Implementation Plan: First Working Version (V1) - Printable Worksheet Loop

**Branch**: `001-build-first-working` | **Date**: 2026-06-14 | **Spec**: `specs/001-build-first-working/spec.md`

**Input**: Feature specification from `/specs/001-build-first-working/spec.md`

## Summary

Deliver the first fully usable local loop for parent-led Kumon practice: generate a short Greek worksheet, print it, and keep local profile/history continuity. Arithmetic and worksheet content are deterministic Python outputs; LLM is configured for optional explanatory use only and is not required for the core workflow.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Typer, Rich, Jinja2, Pydantic, FastAPI (stub), LangGraph + langchain-openai (bounded agent layer), OpenAI SDK (local endpoint compatibility)

**Storage**: SQLite (local file under `data/kumon.db`)

**Testing**: pytest

**Target Platform**: Local macOS/Linux/Windows developer machine

**Project Type**: Single-project Python application (CLI-first, web/API-ready)

**Performance Goals**:
- Generate 15-exercise worksheet + answer key in under 1 second on a typical laptop.
- Complete CLI command startup under 1 second for read/list commands.

**Constraints**:
- Local-first operation, no mandatory internet access.
- Child-facing content defaults to Greek.
- Deterministic arithmetic from code only (no LLM scoring).

**Scale/Scope**:
- v1 single household, low concurrency.
- 10-100 worksheets per child in local history for initial usage.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Deterministic before agentic**: PASS - worksheet generation is pure Python.
- **Arithmetic truth from code**: PASS - answers computed in domain math engine.
- **Inspectable progression**: PASS (for v1 scope where progression is informational).
- **Parent override authority**: PASS by design target; full override workflows planned for later milestones.
- **Paper workflow first**: PASS - generate/print loop is the primary feature.
- **Short and incremental assignments**: PASS - default 15 exercises.
- **Greek-first**: PASS - worksheet content and skill text default Greek.
- **Local-first**: PASS - SQLite + local LLM endpoint configuration.
- **Shared domain logic**: PASS - service layer shared by CLI and future web routes.
- **In-app documentation**: PASS - CLI explain commands from embedded knowledge base.

No constitutional violations identified for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/001-build-first-working/
├── plan.md
├── spec.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── api/
├── agents/
├── cli/
├── domain/
├── persistence/
├── prompts/
├── services/
├── templates/
├── tests/
└── web/

data/
output/
main.py
pyproject.toml
README.md
```

**Structure Decision**: Single Python project with CLI-first entrypoint and layered architecture (`domain` -> `services` -> `transport`), preserving shared business logic between CLI and future FastAPI/web surfaces.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

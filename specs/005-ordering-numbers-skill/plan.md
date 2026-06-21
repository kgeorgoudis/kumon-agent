# Implementation Plan: Ordering Numbers Skill

**Branch**: `main` | **Date**: 2026-06-21 | **Spec**: `specs/005-ordering-numbers-skill/spec.md`

**Input**: Feature specification from `/specs/005-ordering-numbers-skill/spec.md`

## Summary

Implement the missing `ordering_numbers` micro-skill end to end by adding a deterministic exercise generator, extending the shared exercise/answer representation to support ordered number sequences, and updating manual submission scoring so sequence answers can be normalized and checked deterministically. Keep the feature local-first, Greek-first, and fully reusable from the existing CLI and worksheet-rendering pipeline.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Typer, Rich, Jinja2, Pydantic, sqlite3 (stdlib), FastAPI (shared-service readiness), pytest

**Storage**: SQLite (`data/kumon.db`) via `app/persistence/database.py`; worksheet exercises persisted as JSON in `worksheet_instances.exercises_json`; manual answers and score snapshots persisted in existing submission tables

**Testing**: pytest (`app/tests/`) with focused coverage for math engine, worksheet rendering, submission/scoring, and CLI submission flows

**Target Platform**: Local macOS/Linux/Windows environments with offline-first behavior

**Project Type**: Single-project Python application (`app/`) with shared domain/services consumed by CLI and future web UI

**Performance Goals**:
- Generate a default 15-exercise ordering worksheet and answer key in <=10 seconds (`SC-001`).
- Score a completed 15-exercise ordering worksheet in <=1 second after confirmation in normal local operation.
- Preserve deterministic regeneration: identical `micro_skill_id + count + seed` yields identical exercises and answer key (`FR-004`, `SC-002`).

**Constraints**:
- All generation and scoring logic must remain deterministic Python code (`Principles I-II`).
- Child-facing worksheet instructions and rendered problem text must default to Greek (`Principle VII`).
- Feature must work fully offline with existing local persistence and rendering stack (`Principle VIII`).
- If optional LLM narrative is later used to describe ordering progress, it must run under the Kumon Tutor Persona and remain grounded in deterministic scoring payloads (`Principle XI`).
- Existing arithmetic worksheet generation and scalar-answer submission flows must remain backward compatible.
- Current manual submission parsing/scoring assumes one scalar answer per exercise; this feature must extend that path to sequence answers without introducing LLM dependencies.

**Scale/Scope**:
- Single-household usage, typically 10-15 exercises per worksheet.
- Ordering exercises contain 4-6 distinct numbers each, up to 1000.
- v1 scope covers generation, rendering, manual submission/scoring compatibility, and progression compatibility for one micro-skill.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **I. Deterministic Before Agentic**: PASS - generator, normalization, and scoring remain pure Python; no LLM involvement.
- **II. Arithmetic Truth From Code**: PASS - sorted sequences and correctness checks are computed directly from Python data structures.
- **III. Inspectable Progression**: PASS - ordering worksheets continue to produce deterministic score snapshots compatible with existing progress reporting.
- **IV. Parent Override Authority**: PASS - parent still reviews and can correct entered answers before confirmation.
- **V. Paper Workflow First**: PASS - feature closes a missing gap in the core print -> solve -> submit -> score loop.
- **VI. Short and Incremental Assignments**: PASS - design keeps default sheet length and difficulty bounded to small number-ordering sets.
- **VII. Greek-First Content/UI**: PASS - worksheet text and instructions stay Greek-first.
- **VIII. Local-First Architecture**: PASS - uses existing local SQLite + HTML rendering only.
- **IX. Shared Domain Logic**: PASS - generation lives in `app/domain/`, submission/scoring in shared services, reused by CLI and future web routes.
- **X. In-App Documentation**: PASS - no new documentation principle violations; skill already exists in knowledge base and implementation will bring behavior in line with documented availability.
- **XI. Kumon Tutor Persona**: PASS - feature remains deterministic and does not introduce LLM calls; any downstream narrative about ordering results continues to inherit persona constraints from the shared progress-report pipeline.

### Post-Design Re-Check

- PASS - design extends the shared `Exercise` representation instead of introducing a parallel one-off path.
- PASS - manual scoring remains deterministic and inspectable through canonical normalized sequence strings in score snapshots.
- PASS - no persona drift risk introduced because the feature adds no direct LLM orchestration path.
- PASS - no constitution violations identified; Complexity Tracking exceptions not required.

## Phase 0: Research Plan

Research findings are documented in `specs/005-ordering-numbers-skill/research.md` and resolve implementation decisions for:
- How to represent ordering exercises in the existing arithmetic-centric `Exercise` model.
- How to encode ordering direction and canonical answers deterministically.
- How to normalize sequence answers for manual submission and future OCR compatibility.
- How to avoid delimiter conflicts in CLI bulk submission for sequence-based answers.
- How to render clear Greek instructions without creating a separate worksheet pipeline.

## Phase 1: Design & Contracts

Design artifacts produced for implementation:
- `specs/005-ordering-numbers-skill/data-model.md`
- `specs/005-ordering-numbers-skill/contracts/cli.md`
- `specs/005-ordering-numbers-skill/quickstart.md`

Agent context reference updated:
- `.github/copilot-instructions.md` now points to `specs/005-ordering-numbers-skill/plan.md` between `SPECKIT` markers.

## Project Structure

### Documentation (this feature)

```text
specs/005-ordering-numbers-skill/
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
├── domain/
│   ├── math_engine.py             # add ordering_numbers generator + registry entry
│   └── models.py                  # extend Exercise for sequence-based worksheet items
├── services/
│   ├── worksheet_generator.py     # Greek instructions/title behavior and rendering compatibility
│   └── submission_service.py      # sequence-aware answer normalization, parsing, and scoring
├── persistence/
│   └── database.py                # persist/reload extended Exercise JSON unchanged via existing tables
├── templates/
│   ├── worksheet.html.j2          # confirm multi-part ordering prompt renders clearly
│   └── answer_key.html.j2         # confirm ordered sequence answer key formatting
└── tests/
    ├── test_math_engine.py        # new ordering generator and determinism coverage
    ├── test_worksheet_generator.py# worksheet rendering/output coverage
    ├── test_submission_service.py # sequence normalization and scoring coverage
    └── test_cli_submit.py         # ordering-specific submit flow coverage
```

**Structure Decision**: Keep the existing single-project architecture. Implement ordering logic as an extension of the shared domain model and shared submission/scoring services rather than adding a one-off special-case pipeline. This minimizes risk to CLI/web consistency and preserves inspectable score snapshots.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

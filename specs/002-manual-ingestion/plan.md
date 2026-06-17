# Implementation Plan: Manual Exercise Ingestion by Parent

**Branch**: `002-manual-ingestion` | **Date**: 2026-06-17 | **Spec**: `specs/002-manual-ingestion/spec.md`

**Input**: Feature specification from `/specs/002-manual-ingestion/spec.md`

## Summary

Replace OCR-based worksheet ingestion with a manual parent submission flow: the parent selects a worksheet `instance_id`, enters answers quickly (sequential or bulk), reviews/corrects before confirmation, and triggers deterministic scoring immediately on confirm. The implementation removes OCR/vision runtime dependencies from the ingestion path while preserving full local audit linkage (`worksheet -> submission -> score`).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Typer, Rich, Pydantic, SQLite (`sqlite3`), FastAPI (shared-service readiness)

**Storage**: SQLite metadata in `data/kumon.db` (manual submission records + per-answer entries + score snapshots)

**Testing**: pytest (CLI submission flows, validation paths, deterministic scoring, interruption/resume behavior)

**Target Platform**: Local macOS/Linux/Windows machines

**Project Type**: Single-project Python app (`app/`), CLI-first with shared service layer for later web UI

**Performance Goals**:
- Parent completes entry for a 20-exercise sheet in <=2 minutes (SC-001).
- Scoring response displayed in <=1 second after confirmation (SC-002).
- End-to-end submit flow for typical 15-exercise sheet in <=3 minutes (SC-005).

**Constraints**:
- No image upload, OCR, or vision-model dependency in this feature (FR-014).
- Fully local/offline operation with no external services (SC-006).
- Duplicate confirmed submissions for same worksheet instance are rejected (FR-012).
- Submission state must support interruption recovery (FR-013).

**Scale/Scope**:
- Single-household usage pattern.
- Typical volume: 1-5 submissions/day, 10-20 answers per worksheet.
- CLI is primary interface in this phase; web UI is deferred.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **I. Deterministic Before Agentic**: PASS - manual ingestion and scoring are pure code paths; no agentic fallback.
- **II. Arithmetic Truth From Code**: PASS - scoring compares submitted values with deterministic worksheet answers from domain code.
- **III. Inspectable Progression**: PASS - submission and score artifacts are persisted with stable IDs for downstream planner explainability.
- **IV. Parent Override Authority**: PASS - parent reviews and edits all entered values before final confirmation.
- **V. Paper Workflow First**: PASS - workflow remains print -> paper solve -> parent capture -> score.
- **VI. Short and Incremental Assignments**: PASS - feature supports existing 10-20 exercise worksheet lengths efficiently.
- **VII. Greek-First Content/UI**: PASS - parent-facing CLI summaries/results remain Greek-first.
- **VIII. Local-First Architecture**: PASS - no remote dependency added; SQLite-only persistence.
- **IX. Shared Domain Logic**: PASS - CLI command will call shared submission/scoring service modules.
- **X. In-App Documentation**: PASS - CLI help/contract docs cover new submit flow behavior.

### Post-Design Re-Check

- PASS - data model and contracts preserve deterministic, inspectable, local-first behavior.
- PASS - no constitution violations; complexity exemptions not required.

## Phase 0: Research Plan

Research findings are documented in `specs/002-manual-ingestion/research.md` and resolve implementation decisions for:
- Manual entry UX shape (sequential + bulk input with correction loop).
- Validation/normalization strategy for numeric answer inputs.
- Duplicate submission policy and interruption recovery strategy.
- Optional timing capture format and persistence.
- Deterministic scoring trigger and idempotent audit expectations.

## Phase 1: Design & Contracts

Design artifacts produced for implementation:
- `specs/002-manual-ingestion/data-model.md`
- `specs/002-manual-ingestion/contracts/cli.md`
- `specs/002-manual-ingestion/quickstart.md`

Agent context reference updated:
- `.github/copilot-instructions.md` now points to `specs/002-manual-ingestion/plan.md` between `SPECKIT` markers.

## Project Structure

### Documentation (this feature)

```text
specs/002-manual-ingestion/
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
│   └── main.py
├── domain/
│   └── models.py
├── services/
│   ├── scoring_service.py
│   └── submission_service.py   # new
├── persistence/
│   └── database.py
└── tests/
    ├── test_cli_submit.py      # new
    ├── test_submission_service.py  # new
    └── test_scoring_service.py
```

**Structure Decision**: Keep the existing single-project Python architecture and add a dedicated manual submission service in `app/services/`, with persistence extensions in `app/persistence/database.py`; expose behavior via `kumon submit` in CLI while reusing the same service layer for future web routes.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

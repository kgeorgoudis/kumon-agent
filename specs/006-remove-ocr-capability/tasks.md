# Tasks: Remove OCR Capability

**Input**: Design documents from `/specs/006-remove-ocr-capability/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because spec requires deterministic verification and zero regressions.

**Organization**: Tasks grouped by user story and executed phase-by-phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`US1`, `US2`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature artifacts and task baseline.

- [X] T001 [Setup] Create feature docs for implementation in `specs/006-remove-ocr-capability/{plan.md,research.md,data-model.md,quickstart.md}`
- [X] T002 [Setup] Create API/CLI contracts in `specs/006-remove-ocr-capability/contracts/{api.md,cli.md}`
- [X] T003 [Setup] Update context pointer in `.github/copilot-instructions.md` to `specs/006-remove-ocr-capability/plan.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove OCR dependencies and shared model surfaces before story-level cleanup.

- [X] T004 [Foundation] Remove OCR/image dependencies from `pyproject.toml` (`pytesseract`, `pypdfium2`, `pillow`, `python-magic`)
- [X] T005 [Foundation] Remove OCR model types from `app/domain/models.py` (`OcrResult`, `OcrField`, status/source enums, transitions)
- [X] T006 [Foundation] Simplify `ScoreResultSnapshot` model in `app/domain/models.py` to manual-submission-centric schema
- [X] T007 [Foundation] Remove OCR fallback configuration from `app/config.py`

**Checkpoint**: Foundation complete; user-story implementation can proceed.

---

## Phase 3: User Story 1 - Clean Manual Submission Workflow (Priority: P1) 🎯 MVP

**Goal**: Keep `kumon submit` as the only worksheet submission path and remove OCR runtime code.

**Independent Test**: `uv run kumon submit <instance_id> --answers "..." --no-confirm` succeeds and persists deterministic snapshot.

### Tests for User Story 1

- [X] T008 [US1] Remove OCR-specific test modules: `app/tests/test_ingestion_service.py`, `app/tests/test_ocr_review_service.py`, `app/tests/test_rescoring_idempotency.py`, `app/tests/test_llm_client.py`
- [X] T009 [US1] Remove OCR assertions/imports from `app/tests/test_database.py` and simplify shared helpers in `app/tests/__init__.py`

### Implementation for User Story 1

- [X] T010 [US1] Delete OCR runtime modules: `app/services/ingestion_service.py`, `app/services/ocr_review_service.py`, `app/domain/ocr_mapping.py`
- [X] T011 [US1] Remove OCR rescoring path from `app/services/scoring_service.py` and keep manual snapshot persistence only
- [X] T012 [US1] Remove OCR persistence methods from `app/persistence/database.py` and keep backward-compatible schema handling
- [X] T013 [US1] Simplify progress snapshot lookup in `app/persistence/database.py` to `submission_id`-linked snapshots only
- [X] T014 [US1] Remove OCR routes from `app/api/__init__.py`
- [X] T015 [US1] Remove OCR fallback helpers from `app/agents/llm_client.py`

**Checkpoint**: Manual-only submission workflow is active and OCR runtime code removed.

---

## Phase 4: User Story 2 - No Broken Imports or Runtime Errors (Priority: P2)

**Goal**: Ensure CLI/API import stability and documentation alignment after OCR removal.

**Independent Test**: `uv run kumon --help`, `uv run kumon list-skills`, and pytest all succeed.

### Tests for User Story 2

- [X] T016 [US2] Run regression test suite: `uv run pytest app/tests/`

### Implementation for User Story 2

- [X] T017 [US2] Update workflow/docs wording in `app/domain/knowledge_base.py`, `app/agents/__init__.py`, and `app/__init__.py` for manual-only flow
- [X] T018 [US2] Update CLI module documentation in `app/cli/main.py` to reflect manual-only submission

**Checkpoint**: CLI/API entry points are clean with no OCR import paths.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verify completion criteria and track implementation readiness.

- [X] T019 [Polish] Verify checklist completion in `specs/006-remove-ocr-capability/checklists/requirements.md`
- [X] T020 [Polish] Validate quickstart expectations via test run and command checks documented in `specs/006-remove-ocr-capability/quickstart.md`
- [X] T021 [Polish] Ensure task/spec/plan consistency across `specs/006-remove-ocr-capability/{spec.md,plan.md,tasks.md}`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks all stories.
- **US1 (Phase 3)**: depends on Foundational completion.
- **US2 (Phase 4)**: depends on Foundational completion; can run after/alongside US1 where file overlap allows.
- **Polish (Phase 5)**: depends on completion of US1 + US2.

### User Story Dependencies

- **US1 (P1)**: independent MVP once foundation complete.
- **US2 (P2)**: validates import/runtime stability on top of US1 cleanup.

### Parallel Opportunities

- T001-T003 can run in parallel.
- T004 and T007 can run in parallel.
- T008 and T009 can run in parallel.
- T017 and T018 can run in parallel.

---

## Notes

- All tasks are marked complete because implementation and regression verification were already executed in this feature branch.
- Remaining optional step is a manual smoke run of the quickstart commands against local sample data.


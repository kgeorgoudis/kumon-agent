# Tasks: First Working Version (V1) - Printable Worksheet Loop

**Input**: Design documents from `specs/001-build-first-working/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `data-model.md`, `quickstart.md`

**Tests**: Included because the specification explicitly requires automated deterministic tests (FR-009).

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story phases only
- Every task includes an exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure project tooling, directories, and runtime entrypoints are in place for v1.

- [X] T001 Confirm runtime dependencies and CLI script entry in `pyproject.toml`
- [X] T002 Create runtime directories and placeholders in `data/.gitkeep` and `output/worksheets/.gitkeep`
- [X] T003 [P] Configure Python package roots with `__init__.py` files in `app/domain/__init__.py` and `app/services/__init__.py`
- [X] T004 [P] Add developer quickstart usage and architecture notes in `README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain, config, persistence, and shared service wiring required by all stories.

**⚠️ CRITICAL**: No user story work should start until this phase is complete.

- [X] T005 Implement runtime config constants and local-first defaults in `app/config.py`
- [X] T006 Implement core domain entities and enums in `app/domain/models.py`
- [X] T007 Implement deterministic arithmetic generation registry in `app/domain/math_engine.py`
- [X] T008 Implement SQLite schema and repository helpers in `app/persistence/database.py`
- [X] T009 [P] Add local LLM client wrapper with OpenAI-compatible URL config in `app/agents/llm_client.py`
- [X] T010 [P] Add versioned prompt scaffold for bounded explanation tasks in `app/prompts/v1/explain_mistake.md`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Generate and Print a Worksheet (Priority: P1) 🎯 MVP

**Goal**: Parent can generate deterministic Greek worksheet + answer key HTML files for paper solving.

**Independent Test**: Run `uv run kumon generate multiplication-2-5 --exercises 15 --no-open` and verify two HTML outputs with deterministic exercise content.

### Tests for User Story 1

- [X] T011 [P] [US1] Add deterministic seed and arithmetic correctness tests in `app/tests/test_math_engine.py`
- [X] T012 [P] [US1] Add worksheet rendering and output file tests in `app/tests/test_worksheet_generator.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement worksheet HTML print template in `app/templates/worksheet.html.j2`
- [X] T014 [P] [US1] Implement answer key HTML print template in `app/templates/answer_key.html.j2`
- [X] T015 [US1] Implement worksheet generation service orchestration in `app/services/worksheet_generator.py`
- [X] T016 [US1] Implement `generate` command options and validation in `app/cli/main.py`
- [X] T017 [US1] Wire CLI main entrypoint for direct execution in `main.py`
- [X] T018 [US1] Persist generated worksheet metadata after CLI generation in `app/cli/main.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Understand the Method and Skills In-App (Priority: P2)

**Goal**: Parent can access Kumon method guidance, skill explanations, and progression help directly in the app.

**Independent Test**: Run `uv run kumon explain method`, `uv run kumon explain skill multiplication`, and `uv run kumon explain progression` and verify helpful content appears.

### Tests for User Story 2

- [X] T019 [P] [US2] Add knowledge-base coverage tests for method and skill metadata in `app/tests/test_knowledge_base.py`
- [X] T020 [P] [US2] Add CLI explain command output tests in `app/tests/test_cli_explain.py`

### Implementation for User Story 2

- [X] T021 [US2] Implement embedded method/progression/worksheet-type docs in `app/domain/knowledge_base.py`
- [X] T022 [US2] Implement `explain` command group and subcommands in `app/cli/main.py`
- [X] T023 [US2] Implement `list-skills` command with difficulty and Greek descriptions in `app/cli/main.py`
- [X] T024 [US2] Document in-app help flows and parent guidance commands in `README.md`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Save Profiles and Worksheet History Locally (Priority: P3)

**Goal**: Parent can save child profiles and retrieve worksheet history from local SQLite.

**Independent Test**: Run `uv run kumon profile create "Ελένη" --age 10 --grade 4`, generate worksheet with `--child`, then run `uv run kumon history --child "Ελένη"` and verify persisted history.

### Tests for User Story 3

- [X] T025 [P] [US3] Add profile CRUD and worksheet persistence tests in `app/tests/test_database.py`
- [X] T026 [P] [US3] Add CLI profile/history behavior tests in `app/tests/test_cli_profiles_history.py`

### Implementation for User Story 3

- [X] T027 [US3] Implement profile create/list/show subcommands in `app/cli/main.py`
- [X] T028 [US3] Implement history listing command with child filter in `app/cli/main.py`
- [X] T029 [US3] Add child profile lookup and fallback helper logic in `app/cli/main.py`
- [X] T030 [US3] Ensure worksheet-instance save and recent-query methods are complete in `app/persistence/database.py`
- [X] T031 [US3] Add schema indexes and idempotent insert behavior for worksheet records in `app/persistence/database.py`

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Harden quality, clarify docs, and validate quickstart flow end-to-end.

- [X] T032 [P] Add API/web stubs that keep service layer thin in `app/api/__init__.py` and `app/web/__init__.py`
- [X] T033 [P] Add project architecture and constitution alignment notes in `app/__init__.py`
- [X] T034 Run and update full regression suite summary in `README.md` based on `uv run pytest -v`
- [X] T035 Validate quickstart commands and expected outputs in `specs/001-build-first-working/quickstart.md`
- [X] T036 Add final release notes for v1 scope and known out-of-scope items in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all story work.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2; can run parallel with Phase 5 once Phase 2 is complete.
- **Phase 5 (US3)**: Depends on Phase 2; can run parallel with Phase 4 once Phase 2 is complete.
- **Phase 6 (Polish)**: Depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories; delivers MVP on its own.
- **US2 (P2)**: Depends on foundational modules but is independently testable from US1.
- **US3 (P3)**: Depends on foundational persistence but is independently testable from US2.

### Within Each User Story

- Write tests first and confirm they fail before implementation.
- Implement templates/models before service orchestration where relevant.
- Implement service logic before CLI transport wiring.
- Complete story-level validation before moving to next priority.

### Parallel Opportunities

- Setup tasks marked `[P]` can run in parallel (`T003`, `T004`).
- Foundational tasks marked `[P]` can run in parallel (`T009`, `T010`).
- In each story, marked test tasks and template tasks can run in parallel.
- After Phase 2, US2 and US3 can proceed in parallel if staffing allows.

---

## Parallel Example: User Story 1

```bash
# Run US1 test authoring in parallel:
Task: T011 [US1] app/tests/test_math_engine.py
Task: T012 [US1] app/tests/test_worksheet_generator.py

# Run US1 template implementation in parallel:
Task: T013 [US1] app/templates/worksheet.html.j2
Task: T014 [US1] app/templates/answer_key.html.j2
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) and run US1 independent test.
3. Demo printable worksheet generation loop.

### Incremental Delivery

1. Deliver MVP (US1) for immediate parent use.
2. Add US2 for in-app method guidance and confidence.
3. Add US3 for continuity via local profile/history persistence.
4. Finish with Phase 6 hardening and docs alignment.

### Parallel Team Strategy

1. One developer finalizes foundation (`T005`-`T010`).
2. Developer A drives US1; Developer B drives US2; Developer C drives US3 after Phase 2.
3. Merge at phase checkpoints with full test validation.


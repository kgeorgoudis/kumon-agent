# Tasks: List Pending Worksheets

**Input**: Design documents from `/specs/003-list-pending-worksheets/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Include deterministic pytest coverage for persistence and CLI flows because the specification defines independent acceptance scenarios per user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- `[P]` marks tasks that can run in parallel (different files, no blocking dependency).
- `[Story]` labels appear only in user-story phases (`[US1]`, `[US2]`).

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature scaffolding for pending worksheet listing.

- [X] T001 Create feature task baseline in `specs/003-list-pending-worksheets/tasks.md`
- [X] T002 [P] Add pending command test scaffold in `app/tests/test_cli_pending.py`
- [X] T003 [P] Add persistence pending-query test scaffold in `app/tests/test_database.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared query/projection components required by all stories.

**⚠️ CRITICAL**: Complete this phase before starting any user story.

- [X] T004 Add pending worksheet projection model in `app/domain/models.py`
- [X] T005 Add database query method to list worksheets without confirmed submissions in `app/persistence/database.py`
- [X] T006 Add child-filter and limit support to pending query in `app/persistence/database.py`
- [X] T007 Add draft-state indicator fields (`has_draft_submission`, `latest_draft_submission_id`) in pending query projection in `app/persistence/database.py`
- [X] T008 Add service helper to fetch pending worksheets from persistence in `app/services/submission_service.py`

**Checkpoint**: Foundation ready; user stories can now be implemented.

---

## Phase 3: User Story 1 - List Unsubmitted Worksheets (Priority: P1) 🎯 MVP

**Goal**: Parent can run `kumon pending` and retrieve copyable worksheet IDs for all unsubmitted worksheets.

**Independent Test**: Generate multiple worksheets, confirm one submission, run `kumon pending`, and verify only pending worksheets appear with full IDs.

### Tests for User Story 1

- [X] T009 [P] [US1] Add DB test for excluding confirmed submissions in `app/tests/test_database.py`
- [X] T010 [P] [US1] Add DB test for including draft/cancelled submissions as pending in `app/tests/test_database.py`
- [X] T011 [P] [US1] Add CLI test for `kumon pending` happy path with full IDs in `app/tests/test_cli_pending.py`
- [X] T012 [P] [US1] Add CLI test for empty pending list message in `app/tests/test_cli_pending.py`

### Implementation for User Story 1

- [X] T013 [US1] Add `pending` command to CLI with Greek table output in `app/cli/main.py`
- [X] T014 [US1] Render full `instance_id` (untruncated) and required columns in `app/cli/main.py`
- [X] T015 [US1] Wire CLI command to service helper and default sort order in `app/cli/main.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Filter Pending Worksheets by Child (Priority: P2)

**Goal**: Parent can restrict pending list to one child with `--child`.

**Independent Test**: Create worksheets for two children, run `kumon pending --child <name>`, verify only target child rows appear.

### Tests for User Story 2

- [X] T016 [P] [US2] Add DB test for child_id filter behavior in `app/tests/test_database.py`
- [X] T017 [P] [US2] Add CLI test for `kumon pending --child` filtered rows in `app/tests/test_cli_pending.py`
- [X] T018 [P] [US2] Add CLI test for no-results message with child filter in `app/tests/test_cli_pending.py`

### Implementation for User Story 2

- [X] T019 [US2] Add `--child/-c` and `--limit/-n` options to `pending` command in `app/cli/main.py`
- [X] T020 [US2] Reuse `_resolve_child` semantics to map child name to child_id in `app/cli/main.py`
- [X] T021 [US2] Add Greek no-results messaging variant for child-filtered output in `app/cli/main.py`

**Checkpoint**: User Stories 1 and 2 are independently functional.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and regression validation.

- [X] T022 [P] Update CLI usage examples to include `kumon pending` in `app/cli/main.py` module docstring
- [X] T023 [P] Add pending command usage notes in `README.md`
- [X] T024 Run focused pytest suite and capture quickstart validation notes in `specs/003-list-pending-worksheets/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all story work.
- **Phase 3 (US1)**: depends on Phase 2 only (MVP path).
- **Phase 4 (US2)**: depends on Phase 2 and integrates with US1 command path.
- **Final Phase (Polish)**: depends on selected stories being complete.

### User Story Dependencies

- **US1 (P1)**: starts after foundational phase; no dependency on other stories.
- **US2 (P2)**: starts after foundational phase; reuses US1 command/service path but remains independently testable.

### Within Each User Story

- Write tests first and confirm they fail before implementation.
- Implement persistence/service behavior before CLI wiring.
- Complete story-specific assertions before moving to next story.

---

## Parallel Opportunities

- **Setup**: `T002` and `T003` can run in parallel.
- **Foundational**: `T005` and `T008` can be parallelized after `T004` if interfaces are agreed.
- **US1**: `T009`-`T012` can run in parallel; `T013`/`T014` can split once command skeleton exists.
- **US2**: `T016`-`T018` parallel; `T019` and `T021` can split after filter wiring.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring (US1)
Task T009 in app/tests/test_database.py
Task T010 in app/tests/test_database.py
Task T011 in app/tests/test_cli_pending.py
Task T012 in app/tests/test_cli_pending.py

# Parallel implementation split after CLI command skeleton
Task T014 in app/cli/main.py
Task T015 in app/cli/main.py
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Deliver Phase 3 (`kumon pending` base list + full IDs).
4. Validate US1 independently via CLI and tests.

### Incremental Delivery

1. Ship US1 pending list command.
2. Add US2 child filtering and targeted empty-state messaging.
3. Finish docs and regression validation.

### Parallel Team Strategy

1. One developer handles persistence/query (`T004`-`T007`).
2. One developer handles tests (`T009`-`T012`, `T016`-`T018`).
3. One developer handles CLI/docs (`T013`-`T015`, `T019`-`T024`).


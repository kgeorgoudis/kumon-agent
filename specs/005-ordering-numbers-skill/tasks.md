# Tasks: Ordering Numbers Skill

**Input**: Design documents from `/specs/005-ordering-numbers-skill/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Include pytest tasks for each user story because this feature changes deterministic generation, manual scoring behavior, and progression logic.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story phases only
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new progression scaffolding used by later phases.

- [X] T001 Create deterministic progression service scaffold in `app/services/progression_service.py`
- [X] T002 [P] Create progression service test scaffold in `app/tests/test_progression_service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared model and persistence changes required by worksheet generation, scoring, and progression.

**⚠️ CRITICAL**: No user story work starts before this phase is complete.

- [X] T003 Extend `Exercise` with optional ordering-specific fields in `app/domain/models.py`
- [X] T004 Preserve ordering exercise JSON round-trip in `app/persistence/database.py`
- [X] T005 [P] Add regression tests for extended ordering exercise persistence in `app/tests/test_database.py`

**Checkpoint**: Foundation ready; user stories can now be implemented.

---

<a id="us1"></a>
## Phase 3: User Story 1 - Generate Ordering Numbers Worksheet (Priority: P1) 🎯 MVP

**Goal**: Parent can generate a printable `ordering_numbers` worksheet with deterministic ascending/descending ordering exercises and a matching answer key.

**Independent Test**: Run `uv run kumon generate ordering-numbers --exercises 6 --seed 42 --no-open` and verify a printable worksheet and answer key are generated with stable exercise text for the same seed.

### Tests for User Story 1

- [X] T006 [P] [US1] Add ordering generator validity and determinism tests in `app/tests/test_math_engine.py`
- [X] T007 [P] [US1] Add worksheet and answer-key rendering tests for ordering exercises in `app/tests/test_worksheet_generator.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement the `ordering_numbers` generator and register it in `app/domain/math_engine.py`
- [X] T009 [US1] Add Greek ordering instructions and sequence-friendly worksheet metadata in `app/services/worksheet_generator.py`
- [X] T010 [P] [US1] Adjust worksheet prompt rendering for longer ordering sequences in `app/templates/worksheet.html.j2`
- [X] T011 [P] [US1] Adjust answer-key rendering for sequence answers in `app/templates/answer_key.html.j2`

**Checkpoint**: US1 is independently functional and testable from the existing `kumon generate` command.

---

<a id="us2"></a>
## Phase 4: User Story 2 - Score Ordering Numbers Submission (Priority: P2)

**Goal**: Parent can submit completed `ordering_numbers` answers and receive deterministic sequence-aware scoring.

**Independent Test**: Generate an ordering worksheet, submit known correct and incorrect ordered sequences through the existing submit flow, and verify correct per-exercise scoring and final accuracy.

### Tests for User Story 2

- [X] T012 [P] [US2] Add ordering sequence normalization and scoring tests in `app/tests/test_submission_service.py`
- [X] T013 [P] [US2] Add CLI submit tests for semicolon-delimited bulk ordering answers in `app/tests/test_cli_submit.py`
- [X] T014 [P] [US2] Add confirmed ordering submission and score snapshot regression tests in `app/tests/test_database.py`

### Implementation for User Story 2

- [X] T015 [US2] Implement ordering-aware bulk answer parsing and normalization in `app/services/submission_service.py`
- [X] T016 [US2] Implement canonical sequence scoring for ordering exercises in `app/services/submission_service.py`
- [X] T017 [US2] Update submit command help text and ordering answer examples in `app/cli/main.py`

**Checkpoint**: US2 is independently functional and testable through the existing `kumon submit` command.

---

<a id="us3"></a>
## Phase 5: User Story 3 - Progression Integration (Priority: P3)

**Goal**: `ordering_numbers` participates in deterministic progression decisions and produces inspectable next-step recommendations like other micro-skills.

**Independent Test**: Simulate three scored `ordering_numbers` worksheets with high accuracy, run the progression service, and verify it returns the expected advance/stay/step-back decision plus machine-readable rationale.

### Tests for User Story 3

- [X] T018 [P] [US3] Add progression rule tests for repeated `ordering_numbers` submissions in `app/tests/test_progression_service.py`
- [X] T019 [P] [US3] Add progress-history regression tests covering `ordering_numbers` score snapshots in `app/tests/test_database.py`

### Implementation for User Story 3

- [X] T020 [US3] Implement deterministic progression decision logic for recent worksheet accuracy in `app/services/progression_service.py`
- [X] T021 [US3] Add `ProgressDecision` persistence schema and helpers in `app/persistence/database.py`
- [X] T022 [US3] Trigger progression decision creation after confirmed worksheet scoring in `app/services/submission_service.py`

**Checkpoint**: US3 is independently functional and testable through the new shared progression service.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, regression validation, and end-to-end checks across all stories.

- [X] T023 [P] Add ordering_numbers usage notes and bulk-submit examples in `README.md`
- [X] T024 [P] Add final quickstart validation notes for ordering generation, scoring, and progression in `specs/005-ordering-numbers-skill/quickstart.md`
- [X] T025 Run the focused regression suite and record results in `specs/005-ordering-numbers-skill/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2 and uses the ordering worksheet shape delivered in US1.
- **Phase 5 (US3)**: Depends on Phase 2 and consumes deterministic scoring outputs from US2.
- **Final Phase (Polish)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: First deliverable and MVP; no dependency on other user stories after foundation.
- **US2 (P2)**: Depends on the ordering exercise format introduced in US1 for realistic end-to-end validation.
- **US3 (P3)**: Depends on confirmed deterministic score data from US2.

### Within Each User Story

- Tests are written first and expected to fail before implementation.
- Shared domain/model changes precede service changes.
- Service changes precede CLI/documentation updates.
- Story validation happens before moving to the next priority.

### Parallel Opportunities

- Setup scaffold tasks `T001` and `T002` can overlap after file creation order is agreed.
- Foundational persistence test `T005` can be prepared in parallel with `T003`/`T004` once field names are settled.
- US1 tests `T006` and `T007` can run in parallel.
- US1 template tasks `T010` and `T011` can run in parallel after generator output is defined.
- US2 tests `T012`, `T013`, and `T014` can run in parallel.
- US3 tests `T018` and `T019` can run in parallel.
- Final documentation tasks `T023` and `T024` can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel test tasks for US1
Task: T006 [US1] in app/tests/test_math_engine.py
Task: T007 [US1] in app/tests/test_worksheet_generator.py

# Parallel rendering tasks after generator/service output is stable
Task: T010 [US1] in app/templates/worksheet.html.j2
Task: T011 [US1] in app/templates/answer_key.html.j2
```

## Parallel Example: User Story 2

```bash
# Parallel sequence-scoring tests
Task: T012 [US2] in app/tests/test_submission_service.py
Task: T013 [US2] in app/tests/test_cli_submit.py
Task: T014 [US2] in app/tests/test_database.py
```

## Parallel Example: User Story 3

```bash
# Parallel progression validation tests
Task: T018 [US3] in app/tests/test_progression_service.py
Task: T019 [US3] in app/tests/test_database.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver US1 (`T006`-`T011`) so `kumon generate ordering-numbers` works deterministically.
3. Validate worksheet rendering and answer key generation.
4. Demo/deploy MVP fix for the current `ValueError`.

### Incremental Delivery

1. Add US1 to unblock worksheet generation.
2. Add US2 to complete deterministic submission/scoring for ordered sequences.
3. Add US3 to bring `ordering_numbers` into inspectable progression decisions.
4. Finish with documentation and regression validation.

### Suggested MVP Scope

- **MVP = User Story 1 only**: fix the advertised-but-broken skill so parents can generate printable `ordering_numbers` worksheets.

---

## Notes

- `[P]` tasks are chosen to minimize file overlap and merge conflicts.
- All story tasks include `[US#]` labels for traceability.
- The repo currently has no existing progression service module, so US3 explicitly introduces one instead of assuming hidden planner behavior.
- Sequence-answer support must remain backward compatible with all existing scalar-answer worksheets.

[US1]: https://example.invalid/us1
[US2]: https://example.invalid/us2
[US3]: https://example.invalid/us3

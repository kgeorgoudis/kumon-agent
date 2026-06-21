# Tasks: Ordering Numbers Skill

**Input**: Design documents from `/specs/005-ordering-numbers-skill/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/cli.md`, `quickstart.md`

**Tests**: Include pytest tasks because the spec explicitly requires deterministic generation/scoring validation.

**Organization**: Tasks are grouped by user story so each story can be delivered and tested independently.

## Phase 1: Setup (Project Preparation)

**Purpose**: Prepare feature-specific docs and validation commands used across all stories.

- [X] T001 Confirm ordering quickstart command set and validation checklist in `specs/005-ordering-numbers-skill/quickstart.md`
- [X] T002 [P] Confirm CLI behavior contract examples for generation/submission in `specs/005-ordering-numbers-skill/contracts/cli.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared model/persistence compatibility needed by generation, scoring, and progression.

**⚠️ CRITICAL**: Complete this phase before user-story work.

- [X] T003 Extend ordering-specific optional fields in `Exercise` model in `app/domain/models.py`
- [X] T004 Preserve extended `Exercise` JSON round-trip for worksheet persistence in `app/persistence/database.py`
- [X] T005 [P] Add persistence regression coverage for ordering exercise serialization in `app/tests/test_database.py`

**Checkpoint**: Foundation is complete; user stories can proceed.

---

## Phase 3: User Story 1 - Generate Ordering Numbers Worksheet (Priority: P1) 🎯 MVP

**Goal**: Parent can generate deterministic printable `ordering_numbers` worksheets and answer keys.

**Independent Test**: Run `uv run kumon generate ordering-numbers --exercises 6 --seed 42 --no-open`; verify worksheet + answer key exist and repeat exactly for same seed.

### Tests for User Story 1

- [X] T006 [P] [US1] Add ordering generator validity/determinism tests in `app/tests/test_math_engine.py`
- [X] T007 [P] [US1] Add ordering worksheet/answer-key rendering tests in `app/tests/test_worksheet_generator.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement and register `ordering_numbers` generator logic in `app/domain/math_engine.py`
- [X] T009 [US1] Add ordering Greek instruction/title behavior in `app/services/worksheet_generator.py`
- [X] T010 [P] [US1] Ensure ordering prompt readability in worksheet rendering template `app/templates/worksheet.html.j2`
- [X] T011 [P] [US1] Ensure ordered sequence readability in answer-key template `app/templates/answer_key.html.j2`
- [X] T012 [US1] Verify CLI skill slug path generates `ordering-numbers` without error in `app/cli/main.py`

**Checkpoint**: US1 is independently testable and shippable as MVP.

---

## Phase 4: User Story 2 - Score Ordering Numbers Submission (Priority: P2)

**Goal**: Parent can submit ordering answers and receive deterministic sequence-aware scoring.

**Independent Test**: Submit known-correct and known-incorrect ordering sequences through `kumon submit` and verify per-exercise correctness and final accuracy.

### Tests for User Story 2

- [X] T013 [P] [US2] Add ordering normalization and scoring tests in `app/tests/test_submission_service.py`
- [X] T014 [P] [US2] Add semicolon-delimited bulk submit tests in `app/tests/test_cli_submit.py`
- [X] T015 [P] [US2] Add score snapshot regression for ordering submissions in `app/tests/test_database.py`

### Implementation for User Story 2

- [X] T016 [US2] Implement semicolon-aware bulk answer parsing for ordering worksheets in `app/services/submission_service.py`
- [X] T017 [US2] Implement canonical sequence normalization/comparison for ordering answers in `app/services/submission_service.py`
- [X] T018 [US2] Update submit command examples/help for ordering answer format in `app/cli/main.py`

**Checkpoint**: US2 is independently functional via manual submission flow.

---

## Phase 5: User Story 3 - Progression Integration (Priority: P3)

**Goal**: `ordering_numbers` results feed deterministic progression decisions with inspectable rationale.

**Independent Test**: Simulate three confirmed ordering submissions and verify progression decision output (advance/stay/step-back) follows existing deterministic rules.

### Tests for User Story 3

- [X] T019 [P] [US3] Add progression behavior tests for ordering worksheet history in `app/tests/test_progression_service.py`
- [X] T020 [P] [US3] Add progress-point extraction regression for ordering snapshots in `app/tests/test_database.py`

### Implementation for User Story 3

- [X] T021 [US3] Ensure confirmed ordering submissions emit progression-ready points in `app/services/submission_service.py`
- [X] T022 [US3] Validate ordering skill flow through deterministic progression decisions in `app/services/progression_service.py`

**Checkpoint**: US3 is independently testable with deterministic progression output.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Complete docs and execute full focused regression for the feature.

- [X] T023 [P] Add ordering generation/submission usage notes in `README.md`
- [X] T024 [P] Update feature quickstart with final verification steps and observed outputs in `specs/005-ordering-numbers-skill/quickstart.md`
- [X] T025 Run focused regression suite and record results in `specs/005-ordering-numbers-skill/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 -> no dependencies.
- Phase 2 -> depends on Phase 1 and blocks all story work.
- Phase 3 (US1) -> depends on Phase 2.
- Phase 4 (US2) -> depends on Phase 2 and uses ordering worksheet structures from US1.
- Phase 5 (US3) -> depends on Phase 2 and deterministic scoring outputs from US2.
- Final Phase -> depends on all completed stories.

### User Story Dependencies

- **US1 (P1)**: standalone MVP after foundation.
- **US2 (P2)**: depends on ordering exercise format delivered by US1.
- **US3 (P3)**: depends on confirmed score data from US2.

### Parallel Opportunities

- `T006` and `T007` can run in parallel (different test files).
- `T010` and `T011` can run in parallel (different templates).
- `T013`, `T014`, and `T015` can run in parallel (different test files).
- `T019` and `T020` can run in parallel (different test files).
- `T023` and `T024` can run in parallel (different docs).

---

## Parallel Example: User Story 1

```bash
Task T006 in app/tests/test_math_engine.py
Task T007 in app/tests/test_worksheet_generator.py
Task T010 in app/templates/worksheet.html.j2
Task T011 in app/templates/answer_key.html.j2
```

## Parallel Example: User Story 2

```bash
Task T013 in app/tests/test_submission_service.py
Task T014 in app/tests/test_cli_submit.py
Task T015 in app/tests/test_database.py
```

## Parallel Example: User Story 3

```bash
Task T019 in app/tests/test_progression_service.py
Task T020 in app/tests/test_database.py
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Finish Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) and validate deterministic worksheet generation.
3. Stop and demo the repaired `ordering-numbers` generation flow.

### Incremental Delivery

1. Add US1 (generation).
2. Add US2 (submission/scoring).
3. Add US3 (progression integration).
4. Finish polish + regression evidence.

### Suggested MVP Scope

- **MVP = User Story 1** (`T006`-`T012`).

---

## Notes

- All tasks follow the required checklist format: `- [ ] T### [P?] [US?] Description with file path`.
- Story labels appear only in user-story phases.
- Sequence-answer behavior must remain backward compatible for scalar worksheets.

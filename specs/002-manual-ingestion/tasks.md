# Tasks: Manual Exercise Ingestion by Parent

**Input**: Design documents from `/specs/002-manual-ingestion/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Include deterministic pytest coverage for service and CLI flows because the feature spec defines independent test criteria per user story and the plan requires CLI/scoring validation.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- `[P]` marks tasks that can run in parallel (different files, no blocking dependency).
- `[Story]` labels appear only in user-story phases (`[US1]`, `[US2]`, `[US3]`).

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature scaffolding and docs for manual ingestion implementation.

- [X] T001 Create manual ingestion task plan baseline in `specs/002-manual-ingestion/tasks.md`
- [X] T002 [P] Add manual ingestion module scaffold in `app/services/submission_service.py`
- [X] T003 [P] Add service test scaffold for manual submission flows in `app/tests/test_submission_service.py`
- [X] T004 [P] Add CLI test scaffold for submit command flows in `app/tests/test_cli_submit.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared data model and persistence capabilities required by all stories.

**⚠️ CRITICAL**: Complete this phase before starting any user story.

- [X] T005 Add manual submission domain enums/models (`ManualSubmission`, `ManualAnswerEntry`, status enums) in `app/domain/models.py`
- [X] T006 Extend score snapshot model linkage to `submission_id` in `app/domain/models.py`
- [X] T007 Add SQLite tables/indexes for manual submissions and answer entries in `app/persistence/database.py`
- [X] T008 Add database CRUD methods for draft/confirmed manual submissions in `app/persistence/database.py`
- [X] T009 Add database CRUD methods for manual answer entries and slot updates in `app/persistence/database.py`
- [X] T010 Add score snapshot persistence/query updates keyed by `submission_id` in `app/persistence/database.py`
- [X] T011 Implement answer normalization and validation helpers in `app/services/submission_service.py`
- [X] T012 Implement deterministic scoring input hash path for manual submissions in `app/services/scoring_service.py`

**Checkpoint**: Foundation ready; user stories can now be implemented.

---

## Phase 3: User Story 1 - Submit Answers for a Completed Worksheet (Priority: P1) 🎯 MVP

**Goal**: Parent submits worksheet answers (sequential or bulk) and gets immediate deterministic score.

**Independent Test**: Generate worksheet, run `kumon submit <instance_id>` with known answers, confirm submission, and verify persisted answers + score output are deterministic.

### Tests for User Story 1

- [X] T013 [P] [US1] Add service test for confirmed bulk submission persistence and scoring in `app/tests/test_submission_service.py`
- [X] T014 [P] [US1] Add service test for sequential answer capture ordering by slot index in `app/tests/test_submission_service.py`
- [X] T015 [P] [US1] Add CLI test for `kumon submit <instance_id> --answers` happy path in `app/tests/test_cli_submit.py`
- [X] T016 [P] [US1] Add CLI test for unknown worksheet error (`ERR_WORKSHEET_NOT_FOUND`) in `app/tests/test_cli_submit.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement submission initialization and worksheet lookup guards in `app/services/submission_service.py`
- [X] T018 [US1] Implement bulk answer parsing/count validation (`ERR_ANSWER_COUNT_MISMATCH`) in `app/services/submission_service.py`
- [X] T019 [US1] Implement confirm-and-score application flow (persist submission -> persist entries -> score snapshot) in `app/services/submission_service.py`
- [X] T020 [US1] Add `submit` command arguments/options and error mapping in `app/cli/main.py`
- [X] T021 [US1] Implement interactive sequential prompting for per-slot answers in `app/cli/main.py`
- [X] T022 [US1] Implement Greek-friendly success/result rendering for submission + score in `app/cli/main.py`
- [X] T023 [US1] Enforce duplicate confirmed submission rejection (`ERR_SUBMISSION_ALREADY_CONFIRMED`) in `app/services/submission_service.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Review and Correct Answers Before Submission (Priority: P2)

**Goal**: Parent reviews all entered answers, corrects individual slots, and confirms corrected values for scoring.

**Independent Test**: Enter answers, edit one slot during review, confirm, and verify corrected value is persisted and used in scoring.

### Tests for User Story 2

- [X] T024 [P] [US2] Add service test for targeted slot correction before confirmation in `app/tests/test_submission_service.py`
- [X] T025 [P] [US2] Add service test for draft resume/restart behavior after interruption in `app/tests/test_submission_service.py`
- [X] T026 [P] [US2] Add CLI test for interactive review-and-correct loop in `app/tests/test_cli_submit.py`

### Implementation for User Story 2

- [X] T027 [US2] Implement review summary payload generation for all entered answers in `app/services/submission_service.py`
- [X] T028 [US2] Implement targeted answer slot update API for draft submissions in `app/services/submission_service.py`
- [X] T029 [US2] Implement `--resume` draft lookup and error path (`ERR_DRAFT_NOT_FOUND`) in `app/services/submission_service.py`
- [X] T030 [US2] Implement CLI review table and slot correction loop in `app/cli/main.py`
- [X] T031 [US2] Implement graceful cancellation handling (Ctrl+C and explicit cancel) in `app/cli/main.py`

**Checkpoint**: User Stories 1 and 2 are independently functional.

---

## Phase 5: User Story 3 - Record Completion Timing (Priority: P3)

**Goal**: Parent optionally records worksheet completion duration and sees it in stored submission output.

**Independent Test**: Submit with and without `--time`; verify parsed duration persistence and unchanged scoring behavior.

### Tests for User Story 3

- [X] T032 [P] [US3] Add service test for timing parser accepted formats (`SS`, `MM:SS`, `12m`) in `app/tests/test_submission_service.py`
- [X] T033 [P] [US3] Add service test for invalid timing format rejection in `app/tests/test_submission_service.py`
- [X] T034 [P] [US3] Add CLI test for `--time` persistence in submit output flow in `app/tests/test_cli_submit.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement duration parsing/normalization to seconds in `app/services/submission_service.py`
- [X] T036 [US3] Persist optional `duration_seconds` and expose in submission summary DTO in `app/services/submission_service.py`
- [X] T037 [US3] Add `--time` option wiring and Greek timing display in `app/cli/main.py`

**Checkpoint**: All user stories are independently functional.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Clean transition from OCR-centric ingestion to manual submission defaults and finalize docs.

- [X] T038 [P] Remove OCR-specific ingestion command references from user-facing help text in `app/cli/main.py`
- [X] T039 [P] Add migration/backward-compat notes for legacy OCR score snapshots in `app/persistence/database.py`
- [X] T040 [P] Update manual ingestion quickstart validation steps in `specs/002-manual-ingestion/quickstart.md`
- [X] T041 [P] Update root usage docs for `kumon submit` workflow in `README.md`
- [X] T042 Run targeted regression suite and record results notes in `specs/002-manual-ingestion/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all story work.
- **Phase 3 (US1)**: depends on Phase 2 only (MVP path).
- **Phase 4 (US2)**: depends on Phase 2 and reuses US1 submission flow.
- **Phase 5 (US3)**: depends on Phase 2; may reuse US1 CLI/service plumbing.
- **Final Phase (Polish)**: depends on selected stories being complete.

### User Story Dependencies

- **US1 (P1)**: starts after foundational phase; no dependency on other stories.
- **US2 (P2)**: starts after foundational phase; integrates with US1 draft/confirm flow but remains independently testable.
- **US3 (P3)**: starts after foundational phase; integrates with submit flow but remains independently testable.

### Within Each User Story

- Write tests first and confirm they fail before implementation.
- Implement service/domain behavior before CLI wiring.
- Complete story-specific persistence changes before final integration assertions.

---

## Parallel Opportunities

- **Setup**: `T002`, `T003`, and `T004` can run in parallel.
- **Foundational**: `T007` and `T011` can proceed in parallel after `T005`/`T006`; `T012` can proceed after `T010`.
- **US1**: `T013`-`T016` can run in parallel; `T020` and `T022` can be split after `T019`.
- **US2**: `T024`-`T026` parallel; `T027` and `T029` can be parallelized before CLI integration `T030`.
- **US3**: `T032`-`T034` parallel; `T035` and `T037` can proceed concurrently once parser contract is fixed.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring (US1)
Task T013 in app/tests/test_submission_service.py
Task T014 in app/tests/test_submission_service.py
Task T015 in app/tests/test_cli_submit.py
Task T016 in app/tests/test_cli_submit.py

# Parallel implementation split after core service flow
Task T020 in app/cli/main.py
Task T022 in app/cli/main.py
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Deliver Phase 3 (US1 submit + deterministic scoring).
4. Validate US1 independently via CLI and tests.

### Incremental Delivery

1. Ship US1 for immediate OCR-free parent workflow.
2. Add US2 review/correction and resume behavior.
3. Add US3 optional timing capture.
4. Finish polish and documentation updates.

### Parallel Team Strategy

1. One developer handles persistence/domain (`T005`-`T010`).
2. One developer handles service logic/tests (`T011`-`T019`, `T024`-`T029`, `T032`-`T036`).
3. One developer handles CLI/tests/docs (`T020`-`T023`, `T030`-`T031`, `T037`-`T042`).


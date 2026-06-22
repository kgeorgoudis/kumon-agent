# Tasks: LangGraph Agentic Architecture

**Input**: Design documents from `/specs/007-langgraph-agent-architecture/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Include tests because the specification explicitly requires automated coverage for agent behavior and degradation paths (FR-016, SC-004, SC-006).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`, `US4`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare LangGraph scaffolding and prompt/test entry points.

- [X] T001 Update agent orchestration dependencies and script metadata in `pyproject.toml`
- [X] T002 [P] Create LangGraph orchestration module skeleton in `app/agents/agent_graph.py`, `app/agents/state.py`, `app/agents/tools.py`, and `app/agents/traces.py`
- [X] T003 [P] Add agent prompt placeholders for review/planning in `app/prompts/v1/worksheet_review.md` and `app/prompts/v1/next_step_planning.md`
- [X] T004 [P] Add shared model-stub fixtures for offline agent tests in `app/tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared models, persistence, and orchestration contracts that all stories depend on.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [X] T005 Add agent runtime entities (`TutorTaskState`, `TutorStepTrace`, `TutorOutcome`) in `app/domain/models.py`
- [X] T006 Add append-only agent trace schema and persistence methods in `app/persistence/database.py`
- [X] T007 Implement prompt-version resolution and task-to-prompt mapping in `app/agents/prompt_registry.py`
- [X] T008 Implement structured trace writer/reader helpers in `app/agents/traces.py`
- [X] T009 Implement deterministic tool wrappers over existing services in `app/agents/tools.py`
- [X] T010 Implement shared graph factory/executor with typed state transitions in `app/agents/agent_graph.py`
- [X] T011 Export orchestration entry points and contracts in `app/agents/__init__.py`
- [X] T012 Add foundational unit tests for state transitions and trace persistence helpers in `app/tests/test_agent_state.py` and `app/tests/test_agent_traces.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Unified agentic tutor layer for all LLM tasks (Priority: P1) 🎯 MVP

**Goal**: Route progress reporting, worksheet review, and next-step planning through one LangGraph orchestration layer.

**Independent Test**: Run `kumon progress --child "Ελένη"` and verify narrative + suggestions come from the graph path with existing deterministic metrics preserved.

### Tests for User Story 1

- [X] T013 [P] \[US1\] Add progress-through-graph regression tests in `app/tests/test_progress_summary_service.py`
- [X] T014 [P] \[US1\] Add graph entrypoint tests for progress/review/planning tasks in `app/tests/test_agent_graph.py`

### Implementation for User Story 1

- [X] T015 \[US1\] Implement progress-report graph nodes and routing in `app/agents/agent_graph.py`
- [X] T016 \[US1\] Refactor progress narrative flow to use the graph facade in `app/services/progress_summary_service.py`
- [X] T017 \[US1\] Implement worksheet review facade service on top of graph orchestration in `app/services/worksheet_review_service.py`
- [X] T018 \[US1\] Implement next-step planning facade service on top of graph orchestration in `app/services/tutor_planning_service.py`
- [X] T019 \[US1\] Wire shared orchestration facade exports for service consumers in `app/agents/__init__.py`
- [X] T020 \[US1\] Update tutor persona/task prompt contracts for all three responsibilities in `app/prompts/v1/kumon_tutor_persona.md`, `app/prompts/v1/progress_summary.md`, `app/prompts/v1/worksheet_review.md`, and `app/prompts/v1/next_step_planning.md`

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Deterministic truth stays code-owned (Priority: P1)

**Goal**: Guarantee all numeric/factual outputs come from deterministic tools and never from model assertions.

**Independent Test**: With a mock model returning conflicting numbers, verify final reported scores/trends still match deterministic service outputs exactly.

### Tests for User Story 2

- [X] T021 [P] \[US2\] Add conflicting-numbers guardrail tests in `app/tests/test_progress_summary_service.py`
- [X] T022 [P] \[US2\] Add deterministic-tool-only contract tests in `app/tests/test_agent_tools.py`

### Implementation for User Story 2

- [X] T023 \[US2\] Implement deterministic fact-collection tool set for scores/progression/history in `app/agents/tools.py`
- [X] T024 \[US2\] Add graph output validation that rejects model-conflicting numeric facts in `app/agents/agent_graph.py`
- [X] T025 \[US2\] Expose progression and skill-hierarchy helpers for tool consumption in `app/services/progression_service.py`
- [X] T026 \[US2\] Ensure worksheet review uses persisted deterministic score snapshots only in `app/services/worksheet_review_service.py`
- [X] T027 \[US2\] Add deterministic-validation status/error fields for tutor outputs in `app/domain/models.py`

**Checkpoint**: User Stories 1 and 2 work with deterministic truth guarantees.

---

## Phase 5: User Story 3 - Graceful degradation when the model is unavailable (Priority: P2)

**Goal**: Ensure all tutor flows succeed with deterministic-only output when model calls fail.

**Independent Test**: Stop the local model and verify CLI and web progress/reporting still succeed with explicit degraded narrative status.

### Tests for User Story 3

- [X] T028 [P] \[US3\] Add unavailable/timeout/invalid-response fallback tests in `app/tests/test_agent_graph_fallback.py`
- [X] T029 [P] \[US3\] Add CLI degraded-mode regression tests in `app/tests/test_cli_progress.py`
- [X] T030 [P] \[US3\] Add web degraded-mode regression tests in `app/tests/test_web_progress.py`

### Implementation for User Story 3

- [X] T031 \[US3\] Implement graph-level degrade-on-failure transitions and error codes in `app/agents/agent_graph.py`
- [X] T032 \[US3\] Add deterministic fallback suggestion/result builders in `app/agents/tools.py`
- [X] T033 \[US3\] Propagate degraded metadata and fallback content in `app/services/progress_summary_service.py`
- [X] T034 \[US3\] Update CLI degraded-status rendering in `app/cli/main.py`
- [X] T035 \[US3\] Update web degraded-status context mapping in `app/web/progress_view.py`

**Checkpoint**: User Stories 1-3 remain functional offline with graceful degradation.

---

## Phase 6: User Story 4 - Inspectable, versioned agent behavior (Priority: P3)

**Goal**: Make prompt versions and step traces explicit, reviewable, and reproducible.

**Independent Test**: Run the same tutor task twice with identical inputs and verify prompt version and step order are traceable and deterministic.

### Tests for User Story 4

- [X] T036 [P] \[US4\] Add prompt-version and step-trace persistence tests in `app/tests/test_agent_traces.py`
- [X] T037 [P] \[US4\] Add deterministic step-order repeatability tests in `app/tests/test_agent_graph.py`

### Implementation for User Story 4

- [X] T038 \[US4\] Add agent run/step persistence APIs for inspectability in `app/persistence/database.py`
- [X] T039 \[US4\] Implement trace lifecycle integration in graph execution paths in `app/agents/agent_graph.py`
- [X] T040 \[US4\] Attach trace summary and prompt version metadata to progress outputs in `app/services/progress_summary_service.py`
- [X] T041 \[US4\] Attach trace summary and prompt version metadata to review/planning outputs in `app/services/worksheet_review_service.py` and `app/services/tutor_planning_service.py`
- [X] T042 \[US4\] Add prompt registry tests for version/path enforcement in `app/tests/test_prompt_registry.py`

**Checkpoint**: All user stories are independently functional and auditable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, docs alignment, and full feature verification.

- [X] T043 [P] Update architecture documentation for the agent layer in `README.md`
- [X] T044 [P] Add prompt/version maintenance notes for contributors in `app/prompts/v1/README.md`
- [X] T045 Remove remaining ad-hoc LLM call branches superseded by graph facades in `app/services/progress_summary_service.py`
- [X] T046 [P] Update validation and demo commands for this feature in `specs/007-langgraph-agent-architecture/quickstart.md`
- [X] T047 Run full regression suite and record the latest results in `specs/007-langgraph-agent-architecture/quickstart.md`
- [X] T048 [P] Align feature documentation references after implementation in `specs/007-langgraph-agent-architecture/plan.md` and `.github/copilot-instructions.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all user stories.
- **Phase 3-6 (User Stories)**: depend on Phase 2 completion.
- **Phase 7 (Polish)**: depends on completion of targeted user stories.

### User Story Dependencies

- **US1 (P1)**: starts after Phase 2; delivers MVP graph-driven tutor orchestration.
- **US2 (P1)**: starts after Phase 2; can run alongside US1 tests, but merges after US1 core graph scaffolding is in place.
- **US3 (P2)**: depends on US1 graph execution paths and US2 validation contracts.
- **US4 (P3)**: depends on US1 graph execution paths; can be developed in parallel with late US3 work where files do not overlap.

### Recommended Completion Order

1. Setup + Foundational (Phase 1-2)
2. US1 (Phase 3) for MVP
3. US2 (Phase 4) for deterministic guarantees
4. US3 (Phase 5) for graceful offline behavior
5. US4 (Phase 6) for inspectability/versioning
6. Polish (Phase 7)

---

## Parallel Opportunities

- **Setup**: `T002`, `T003`, and `T004` can run in parallel.
- **Foundational**: `T007`, `T008`, and `T009` can run in parallel once `T005`-`T006` define contracts.
- **US1**: `T013` and `T014` can run together; prompt task `T020` can run in parallel with service tasks `T017`-`T018`.
- **US2**: `T021` and `T022` can run together before implementation tasks.
- **US3**: `T028`, `T029`, and `T030` can run together.
- **US4**: `T036` and `T037` can run together; `T040` and `T041` can run in parallel after `T039`.

---

## Parallel Example: User Story 1

```bash
# Parallel test authoring for US1
Task T013: app/tests/test_progress_summary_service.py
Task T014: app/tests/test_agent_graph.py

# Parallel implementation for US1 once graph core exists
Task T017: app/services/worksheet_review_service.py
Task T018: app/services/tutor_planning_service.py
Task T020: app/prompts/v1/*.md
```

## Parallel Example: User Story 3

```bash
# Parallel fallback regression coverage
Task T028: app/tests/test_agent_graph_fallback.py
Task T029: app/tests/test_cli_progress.py
Task T030: app/tests/test_web_progress.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 tasks (`T013`-`T020`).
3. Validate US1 independently via `kumon progress` and US1 tests.
4. Demo/deploy the unified graph orchestration before advancing.

### Incremental Delivery

1. Deliver US1 for unified agent orchestration.
2. Deliver US2 for deterministic truth enforcement.
3. Deliver US3 for graceful degradation.
4. Deliver US4 for inspectability and prompt-version traceability.
5. Finish with Phase 7 polish and full regression.

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1).
- This delivers the core user-requested architecture shift to LangGraph while preserving existing behavior.


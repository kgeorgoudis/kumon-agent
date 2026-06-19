# Tasks: Progress Summary

**Input**: Design documents from `/specs/004-progress-summary/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Include pytest tasks for each user story because this feature changes deterministic progress logic, CLI contract behavior, and web rendering behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story phases only
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create feature scaffolding and baseline files used by later phases.

- [X] T001 Create progress prompt scaffold with JSON output contract in `app/prompts/v1/progress_summary.md`
- [X] T002 Create progress service module scaffold in `app/services/progress_summary_service.py`
- [X] T003 [P] Create CLI progress test module scaffold in `app/tests/test_cli_progress.py`
- [X] T004 [P] Create service progress test module scaffold in `app/tests/test_progress_summary_service.py`
- [X] T005 [P] Create web progress test module scaffold in `app/tests/test_web_progress.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared deterministic building blocks required by all stories.

**⚠️ CRITICAL**: No user story work starts before this phase is complete.

- [X] T006 Add progress report value objects (`ProgressWorksheetPoint`, `SkillProgress`, `ProgressSuggestion`, `ProgressReport`) in `app/domain/models.py`
- [X] T007 Add database projection/query for confirmed scored worksheet history in `app/persistence/database.py`
- [X] T008 Add deterministic trend classification and aggregation helpers in `app/services/progress_summary_service.py`
- [X] T009 Add prompt loading utility and prompt-version constant in `app/services/progress_summary_service.py`
- [X] T010 [P] Add persistence-level tests for progress-history query semantics in `app/tests/test_database.py`
- [X] T011 [P] Add deterministic unit tests for trend classification edge cases in `app/tests/test_progress_summary_service.py`

**Checkpoint**: Foundation ready; user stories can now be implemented.

---

## Phase 3: User Story 1 - View Progress Summary via CLI (Priority: P1) 🎯 MVP

**Goal**: Parent can run `kumon progress` and receive deterministic Greek progress metrics and summary structure.

**Independent Test**: Run `kumon progress --child "<name>" --no-llm` against fixtures and verify date range, trend, per-skill metrics, and no-data message.

### Tests for User Story 1

- [X] T012 [P] [US1] Add deterministic service integration tests for report aggregation in `app/tests/test_progress_summary_service.py`
- [X] T013 [P] [US1] Add CLI contract tests for `kumon progress --no-llm` and no-data behavior in `app/tests/test_cli_progress.py`

### Implementation for User Story 1

- [X] T014 [US1] Implement report assembly (`build_progress_report`) without LLM dependency in `app/services/progress_summary_service.py`
- [X] T015 [US1] Add child-resolution and report retrieval helper for progress command in `app/cli/main.py`
- [X] T016 [US1] Implement `kumon progress` Typer command (`--child`, `--limit`, `--no-llm`) in `app/cli/main.py`
- [X] T017 [US1] Implement Greek CLI rendering for deterministic metrics and per-skill table in `app/cli/main.py`
- [X] T018 [US1] Add CLI help text and usage docs for progress command in `README.md`

**Checkpoint**: US1 is independently functional and testable from CLI without LLM.

---

## Phase 4: User Story 2 - Get Next-Step Suggestions (Priority: P1)

**Goal**: Add LLM-generated Greek narrative and suggestions grounded in deterministic report data.

**Independent Test**: Run service and CLI tests with mocked LLM success/failure; verify grounded suggestions and graceful degraded mode.

### Tests for User Story 2

- [X] T019 [P] [US2] Add service tests for LLM success parsing and grounded suggestion validation in `app/tests/test_progress_summary_service.py`
- [X] T020 [P] [US2] Add service tests for LLM timeout/unavailable fallback behavior in `app/tests/test_progress_summary_service.py`
- [X] T021 [P] [US2] Add CLI tests for narrative/suggestions rendering and degraded warning in `app/tests/test_cli_progress.py`

### Implementation for User Story 2

- [X] T022 [US2] Finalize versioned prompt instructions and JSON schema in `app/prompts/v1/progress_summary.md`
- [X] T023 [US2] Implement structured LLM payload builder from `ProgressReport` deterministic fields in `app/services/progress_summary_service.py`
- [X] T024 [US2] Implement LLM call + JSON response parsing + validation guards in `app/services/progress_summary_service.py`
- [X] T025 [US2] Implement degraded narrative fallback and `llm_error_code` mapping in `app/services/progress_summary_service.py`
- [X] T026 [US2] Update CLI output to include narrative and suggestions while preserving deterministic sections in `app/cli/main.py`

**Checkpoint**: US2 adds actionable LLM assistance without changing deterministic source-of-truth metrics.

---

## Phase 5: User Story 3 - View Progress Summary via Web UI (Priority: P2)

**Goal**: Parent can open `/progress` and view the same progress report in web UI.

**Independent Test**: Request `GET /progress?child=<name>` and verify rendered metrics, suggestions, and empty/degraded states.

### Tests for User Story 3

- [X] T027 [P] [US3] Add web route test for progress page with report data in `app/tests/test_web_progress.py`
- [X] T028 [P] [US3] Add web route tests for empty-state and degraded-mode banner in `app/tests/test_web_progress.py`

### Implementation for User Story 3

- [X] T029 [US3] Add progress page template for metrics, narrative, and suggestions in `app/templates/progress_summary.html.j2`
- [X] T030 [US3] Add web-view adapter utilities for rendering report payload in `app/web/progress_view.py`
- [X] T031 [US3] Implement `GET /progress` route with query params (`child`, `limit`, `llm`) in `app/api/__init__.py`
- [X] T032 [US3] Wire route to shared `progress_summary_service` and template response in `app/api/__init__.py`
- [X] T033 [US3] Document web progress page usage in `README.md`

**Checkpoint**: US3 is independently accessible in browser and uses the same report payload as CLI.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation, and validation across all stories.

- [X] T034 [P] Add regression coverage for CLI/web parity on shared report fields in `app/tests/test_web_progress.py`
- [X] T035 [P] Add focused quickstart validation notes and final commands in `specs/004-progress-summary/quickstart.md`
- [X] T036 Run focused regression suite and record results in `specs/004-progress-summary/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 3 deterministic report path.
- **Phase 5 (US3)**: Depends on Phase 3 service and benefits from Phase 4 narrative support.
- **Final Phase (Polish)**: Depends on target user stories being complete.

### User Story Dependencies

- **US1 (P1)**: First deliverable and MVP; no dependency on other stories after foundation.
- **US2 (P1)**: Depends on US1 report payload to ground suggestions.
- **US3 (P2)**: Depends on shared service from US1 and reuses US2 narrative fields when enabled.

### Within Each User Story

- Tests are written first and expected to fail before implementation.
- Service/domain changes precede CLI or web adapters.
- Rendering and docs follow implementation.

### Parallel Opportunities

- Setup test scaffolds (`T003`-`T005`) run in parallel.
- Foundational tests (`T010`, `T011`) run in parallel with model/query work once stubs exist.
- US1 tests (`T012`, `T013`) run in parallel.
- US2 tests (`T019`-`T021`) run in parallel.
- US3 tests (`T027`, `T028`) run in parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel test tasks for US1
Task: T012 [US1] in app/tests/test_progress_summary_service.py
Task: T013 [US1] in app/tests/test_cli_progress.py

# Then implement command + rendering sequentially
Task: T016 [US1] in app/cli/main.py
Task: T017 [US1] in app/cli/main.py
```

## Parallel Example: User Story 2

```bash
# Parallel LLM behavior tests
Task: T019 [US2] in app/tests/test_progress_summary_service.py
Task: T020 [US2] in app/tests/test_progress_summary_service.py
Task: T021 [US2] in app/tests/test_cli_progress.py
```

## Parallel Example: User Story 3

```bash
# Parallel web tests, then template + route wiring
Task: T027 [US3] in app/tests/test_web_progress.py
Task: T028 [US3] in app/tests/test_web_progress.py
Task: T029 [US3] in app/templates/progress_summary.html.j2
Task: T031 [US3] in app/api/__init__.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver US1 (`T012`-`T018`) with deterministic-only CLI flow.
3. Validate with `--no-llm` path and no-data scenario.
4. Demo/deploy MVP.

### Incremental Delivery

1. Add US1 deterministic report in CLI.
2. Add US2 LLM narrative/suggestions with graceful degradation.
3. Add US3 web page over the same service payload.
4. Finish with polish and regression notes.

### Suggested MVP Scope

- **MVP = User Story 1 only** (`kumon progress --no-llm` deterministic report), then expand to US2 and US3.

---

## Notes

- `[P]` tasks are chosen to minimize file overlap and merge conflicts.
- All story tasks include `[US#]` labels for traceability.
- Deterministic metrics remain source of truth; LLM output is advisory and optional.


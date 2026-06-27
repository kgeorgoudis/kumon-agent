# Tasks: Agent Observability and Traceability

**Input**: Design documents from `/specs/008-agent-observability/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the observability package and wire the new retrieval layer into the existing project layout.

- [x] T001 Create the observability package skeleton in `app/observability/__init__.py` and `app/observability/service.py`.
- [x] T002 [P] Add initial observability test scaffolding in `app/tests/test_observability_service.py` and `app/tests/test_observability_agent_integration.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared persistence and retrieval primitives that all observability stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Extend `app/persistence/database.py` with filtered run retrieval for `agent_runs` and add status/task-type indexes for trace queries.
- [x] T004 Implement `TraceService` in `app/observability/service.py` to load run summaries, step timelines, and sanitized details from SQLite.
- [x] T005 [P] Implement deterministic sanitization helpers for trace context/output snapshots in `app/observability/service.py` so raw PII and secrets are never persisted or returned.

**Checkpoint**: Foundational retrieval and sanitization are ready; the user-story work can now begin.

---

## Phase 3: User Story 1 - Inspect a Single Agent Run (Priority: P1) 🎯 MVP

**Goal**: Let an operator view one tutor run and its step timeline from the CLI or API.

**Independent Test**: Trigger one tutor task run and confirm a single run summary and ordered step timeline can be viewed without reading source code.

### Tests for User Story 1

- [x] T006 [P] [US1] Add service tests in `app/tests/test_observability_service.py` for successful run summary retrieval and step ordering.

### Implementation for User Story 1

- [x] T007 [US1] Implement `TraceService.get_run_details()` in `app/observability/service.py` to return run status, timing, prompt version, error code, and step timeline.
- [x] T008 [US1] Add the `GET /api/v1/traces/{task_id}` and `GET /api/v1/traces/{task_id}/steps` handlers in `app/api/__init__.py`.
- [x] T009 [US1] Add the `kumon traces show` CLI command in `app/cli/main.py` to render a single run summary and step timeline.

**Checkpoint**: User Story 1 is independently testable and provides a usable run-inspection surface.

---

## Phase 4: User Story 2 - Troubleshoot Degraded or Failed Outcomes (Priority: P2)

**Goal**: Let operators discover degraded or failed runs quickly and understand why they happened.

**Independent Test**: Create one successful run and one degraded run, then verify both are listable and contain clear diagnostics through the trace views.

### Tests for User Story 2

- [x] T010 [P] [US2] Extend `app/tests/test_observability_service.py` with tests for filtered run listing, degraded-state diagnostics, and fallback metadata visibility.
- [x] T011 [P] [US2] Add integration coverage in `app/tests/test_observability_agent_integration.py` for a degraded path that stores an error code and fallback reason.

### Implementation for User Story 2

- [x] T012 [US2] Implement `TraceService.list_runs()` in `app/observability/service.py` with status, task-type, and time-window filters.
- [x] T013 [US2] Add the `GET /api/v1/traces` endpoint in `app/api/__init__.py` with filter query parameters for status, task type, hours, limit, and offset.
- [x] T014 [US2] Add the `kumon traces list` and `kumon traces filter` CLI subcommands in `app/cli/main.py` with human-readable summaries and JSON output support.
- [x] T015 [US2] Ensure degraded/failed runs persist fallback metadata and machine-readable error codes in `app/agents/agent_graph.py` or the related trace-emission path.

**Checkpoint**: User Story 2 is independently testable and provides actionable troubleshooting visibility.

---

## Phase 5: User Story 3 - Preserve Auditability for Governance (Priority: P3)

**Goal**: Make observability data durable, linkable, and safe for governance review and regression analysis.

**Independent Test**: Persist multiple runs and confirm the stored records remain linked to their associated steps and can be retrieved later without breaking core tutor workflows.

### Tests for User Story 3

- [x] T016 [P] [US3] Add audit-oriented tests in `app/tests/test_observability_service.py` that verify linked run/step retrieval and stable ordering by execution time.

### Implementation for User Story 3

- [x] T017 [US3] Add run-to-step linkage and chronological ordering support in `app/persistence/database.py` for audit-style retrieval.
- [x] T018 [US3] Ensure observability retrieval remains non-blocking when storage is unavailable by returning warnings and degraded-safe responses from `app/observability/service.py` and `app/api/__init__.py`.
- [x] T019 [US3] Document trace inspection usage and expected behavior in `specs/008-agent-observability/quickstart.md` and `README.md`.

**Checkpoint**: User Story 3 is independently testable and protects governance and regression analysis requirements.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tighten the user experience and ensure the feature is fully verified.

- [x] T020 [P] Update CLI help/usage text in `app/cli/main.py` so `kumon traces --help` documents the new commands clearly.
- [x] T021 Run `uv run pytest app/tests/test_observability_service.py app/tests/test_observability_agent_integration.py` and fix any regressions.
- [x] T022 [P] Review `specs/008-agent-observability/quickstart.md` and `README.md` for consistency with the implemented CLI/API behavior.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user-story work.
- **User Stories (Phases 3–5)**: All depend on Foundational completion.
- **Polish (Phase 6)**: Depends on all requested user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; is the MVP slice.
- **User Story 2 (P2)**: Can start after Foundational and should build on the run-summary service from US1.
- **User Story 3 (P3)**: Can start after Foundational and should reuse the same run/step retrieval primitives.

### Parallel Opportunities

- `T002` can be created in parallel with `T001`.
- `T005` can be implemented in parallel with `T003` and `T004` once the package skeleton exists.
- `T006`, `T010`, and `T016` can be authored in parallel once the foundational service exists.
- `T008` and `T009` can be implemented in parallel after `T007` is complete.
- `T013` and `T014` can be implemented in parallel after `T012` is complete.

### Parallel Example: User Story 1

```bash
# Work on the service and API contract in parallel once the foundational service exists:
# - Implement run-details retrieval in app/observability/service.py
# - Add the trace detail API handlers in app/api/__init__.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (User Story 1).
3. Validate the new run-inspection path with the focused observability tests.
4. Add User Stories 2 and 3 only after the MVP is working.

### Incremental Delivery

1. Add foundational retrieval and sanitization.
2. Ship run inspection (US1) as the MVP.
3. Add degraded-run diagnostics (US2).
4. Add governance/auditability hardening (US3).
5. Finish with polish and regression validation.


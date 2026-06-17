# Feature Specification: First Working Version (V1) - Printable Worksheet Loop

**Feature Branch**: `001-build-first-working`

**Created**: 2026-06-14

**Status**: Draft

**Input**: User description: "As a parent I want to build the first working version of the app using Python, LangGraph, and a local LLM; include in-app documentation because I am not a teacher/Kumon expert."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Generate and Print a Worksheet (Priority: P1)

As a parent, I can generate a short Greek math worksheet and a separate answer key for one micro-skill so my child can solve it on paper immediately.

**Why this priority**: This is the minimal value loop; without printable worksheets the product cannot be used in real life.

**Independent Test**: Run `kumon generate multiplication-2-5 --exercises 15 --no-open`; verify two HTML files are created (worksheet + answer key), contain Greek titles/instructions, and include 15 deterministic exercises.

**Acceptance Scenarios**:

1. **Given** the app is installed, **When** I run `kumon generate addition-single-digit --exercises 10`, **Then** the app creates a worksheet HTML and answer key HTML under `output/worksheets/<date>/`.
2. **Given** I provide `--seed 42`, **When** I generate twice with the same skill/count, **Then** the same exercise set is produced.
3. **Given** a worksheet is generated, **When** I open the HTML, **Then** it is print-friendly (A4 layout) and child-facing text is in Greek.

---

### User Story 2 - Understand the Method and Skills In-App (Priority: P2)

As a non-expert parent, I can read method guidance, skill explanations, and progression rules directly from the app so I can use it correctly without external teaching knowledge.

**Why this priority**: Parent confidence and correct usage are essential; documentation must be available in the app, not only in README files.

**Independent Test**: Run `kumon explain method`, `kumon explain skill multiplication`, and `kumon explain progression`; verify useful content is shown and skill descriptions are available in Greek.

**Acceptance Scenarios**:

1. **Given** I am on CLI, **When** I run `kumon explain method`, **Then** I receive a practical Kumon guide suitable for a parent.
2. **Given** I need skill details, **When** I run `kumon list-skills --verbose`, **Then** I see micro-skills with difficulty and Greek descriptions.

---

### User Story 3 - Save Profiles and Worksheet History Locally (Priority: P3)

As a parent, I can store child profile settings and view generated worksheet history locally so I can continue practice over time.

**Why this priority**: The app must preserve continuity between sessions and remain local-first.

**Independent Test**: Create profile with `kumon profile create`, generate worksheet with `--child`, then run `kumon history`; verify records persist across CLI runs.

**Acceptance Scenarios**:

1. **Given** a profile exists, **When** I generate worksheets for that child, **Then** worksheet metadata is stored in SQLite.
2. **Given** multiple worksheets exist, **When** I run `kumon history --child <name>`, **Then** I see recent worksheets in reverse chronological order.

---

### Edge Cases

- What happens when an unsupported micro-skill is passed to `kumon generate`?
- What happens when the local LLM endpoint is offline? (Core worksheet generation must still work.)
- What happens when the output directory does not yet exist?
- What happens when the same worksheet instance is saved twice?
- How does the app handle missing child profile while `--child` is provided?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate deterministic arithmetic exercises in Python for supported micro-skills.
- **FR-002**: System MUST render printable worksheet and answer key HTML outputs for each generation request.
- **FR-003**: System MUST default child-facing worksheet text to Greek.
- **FR-004**: System MUST expose CLI commands for generating worksheets, listing skills, and viewing history.
- **FR-005**: System MUST provide in-app documentation for method overview, skill explanations, and progression rules.
- **FR-006**: System MUST persist child profiles and worksheet instances in local SQLite storage.
- **FR-007**: System MUST support reproducible worksheet generation using a seed.
- **FR-008**: System MUST keep LLM usage optional and bounded to non-deterministic explanatory tasks.
- **FR-009**: System MUST include automated tests for deterministic generation, persistence, and rendering behavior.

### Key Entities *(include if feature involves data)*

- **ChildProfile**: Child configuration (name, age, grade, preferred worksheet length, locale/language).
- **Exercise**: One generated arithmetic item with operands, operator, computed answer, and display text.
- **WorksheetInstance**: Generated worksheet metadata plus exercise list and rendered file paths.
- **MicroSkillMeta**: Documentation and hierarchy metadata for each micro-skill.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parent can generate a worksheet and answer key in under 60 seconds on a local machine.
- **SC-002**: Repeated generation with same skill/count/seed produces 100% identical exercise text.
- **SC-003**: At least 95% of child-facing worksheet strings are Greek by default for v1 scope.
- **SC-004**: Core test suite (domain + service + persistence) passes locally with no network dependency.

## Assumptions

- The app is used by one household on one local machine in v1.
- OCR ingestion and scoring are out of scope for this feature and will be covered in a later feature.
- Local LLM endpoint (`http://127.0.0.1:8000/v1`) may be unavailable; the core worksheet loop remains functional.
- HTML printing via browser is acceptable for v1 in place of native PDF generation.

# Feature Specification: Progress Summary

**Feature Branch**: `004-progress-summary`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "As a parent, I want to see the progress of my child using the agent LLM. Based on the existing progress through submitted worksheets, I want to get an automated summary and suggestions about the next step using my kumon-agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Progress Summary via CLI (Priority: P1)

As a parent, I want to run a CLI command that gathers all scored worksheets for my child and produces a human-readable progress summary in Greek, including accuracy trends, skills practiced, and areas needing attention.

**Why this priority**: This is the core value of the feature — transforming raw worksheet data into an understandable narrative. The CLI path enables immediate use without web UI dependencies.

**Independent Test**: Can be fully tested by running the CLI command against a database with scored worksheets and verifying that a structured Greek summary is returned with accurate data.

**Acceptance Scenarios**:

1. **Given** the child has 3+ scored worksheets in the database, **When** the parent runs the progress summary command, **Then** the system displays a Greek-language summary with accuracy trend, skills practiced, and overall assessment.
2. **Given** the child has scored worksheets spanning multiple micro-skills, **When** the parent requests the progress summary, **Then** the summary groups results by skill and shows per-skill accuracy.
3. **Given** the child has no scored worksheets, **When** the parent runs the progress summary command, **Then** the system displays a friendly message indicating no data is available yet.

---

### User Story 2 - Get Next-Step Suggestions (Priority: P1)

As a parent, I want the progress summary to include LLM-generated suggestions about what the child should practice next, grounded in the actual worksheet history and scoring data.

**Why this priority**: Suggestions close the feedback loop and make the summary actionable. Without them, the parent must interpret raw data alone.

**Independent Test**: Can be tested by verifying that the LLM receives structured scoring data and returns suggestions that reference specific skills from the child's history.

**Acceptance Scenarios**:

1. **Given** the child has scored worksheets with varying accuracy across skills, **When** the summary is generated, **Then** the suggestions section identifies specific micro-skills to focus on next with a brief rationale in Greek.
2. **Given** the child has consistently high accuracy on a skill, **When** the summary is generated, **Then** the suggestions recommend advancing to the next difficulty level or skill.
3. **Given** the child has recurring low accuracy on a specific micro-skill, **When** the summary is generated, **Then** the suggestions recommend focused practice or stepping back.

---

### User Story 3 - View Progress Summary via Web UI (Priority: P2)

As a parent, I want to see the progress summary on a web dashboard page so I can review it without using the terminal.

**Why this priority**: Provides a more accessible interface for non-technical parents. Depends on P1 service logic being implemented first.

**Independent Test**: Can be tested by navigating to the progress page in a browser and verifying the summary renders correctly with the same data as CLI output.

**Acceptance Scenarios**:

1. **Given** the parent navigates to the progress summary page, **When** scored worksheets exist, **Then** the page displays the summary and suggestions in a readable format.
2. **Given** the parent views the progress page, **When** the summary is loading, **Then** a loading indicator is shown.

---

### Edge Cases

- What happens when there is only 1 scored worksheet? The system should still produce a summary but note that trends require more data.
- What happens when the LLM service is unavailable? The system should display deterministic data (accuracy, scores) without the narrative summary and show an error message about the LLM being unavailable.
- What happens when worksheets span a long time gap (e.g., weeks)? The summary should note the gap and not assume continuous practice.
- What happens when the child profile does not exist? The system should return a clear error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST aggregate all scored worksheets for a given child and compute per-micro-skill accuracy percentages.
- **FR-002**: System MUST compute an accuracy trend (improving, stable, declining) based on the chronological order of scored worksheets.
- **FR-003**: System MUST send structured scoring data (not raw DB rows) to the LLM for narrative generation.
- **FR-004**: System MUST produce a Greek-language narrative summary that includes: overall progress assessment, per-skill performance, and identified strengths/weaknesses.
- **FR-005**: System MUST produce Greek-language next-step suggestions grounded in the child's actual data.
- **FR-006**: System MUST expose the progress summary through both CLI and web UI entry points, using the same underlying service.
- **FR-007**: System MUST gracefully degrade when the LLM is unavailable, showing deterministic data without the narrative.
- **FR-008**: System MUST include the date range of worksheets covered in the summary.
- **FR-009**: System MUST NOT use the LLM to compute scores or accuracy — only to generate narrative text and suggestions.
- **FR-010**: System MUST version the prompt used for summary generation.

### Key Entities

- **ProgressReport**: Aggregated progress data for a child — includes per-skill accuracy, trend direction, date range, worksheet count, and generated narrative.
- **SkillProgress**: Per-micro-skill accuracy history — tracks scores over time for a single micro-skill.
- **ProgressSuggestion**: A single actionable recommendation — includes target micro-skill, rationale, and suggested worksheet type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parent can generate a progress summary in under 10 seconds (excluding LLM latency).
- **SC-002**: The summary accurately reflects 100% of scored worksheets in the database for the child.
- **SC-003**: Next-step suggestions reference specific micro-skills that the child has actually practiced.
- **SC-004**: When the LLM is unavailable, the parent still sees all deterministic progress data within 2 seconds.
- **SC-005**: The summary is readable and understandable by a Greek-speaking parent without technical background.

## Assumptions

- The child has at least one scored worksheet in the database for the summary to be meaningful.
- The existing `ScoreResultSnapshot` and `WorksheetInstance` models provide sufficient data for aggregation.
- The LLM client (`app/agents/llm_client.py`) is already configured and available for use.
- The prompt for summary generation will be stored in `app/prompts/v1/` following the existing pattern.
- Greek is the default output language; English fallback is not required for v1.
- The web UI route will be a simple server-rendered page consistent with the existing Jinja2 approach.


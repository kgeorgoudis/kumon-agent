# Feature Specification: Manual Exercise Ingestion by Parent

**Feature Branch**: `002-manual-ingestion`

**Created**: 2025-01-20

**Status**: Draft

**Input**: User description: "Replace OCR-based ingestion with manual parent entry of child's worksheet answers via CLI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit Answers for a Completed Worksheet (Priority: P1)

The parent's child has finished a printed math worksheet. The parent sits down at the computer, runs `kumon submit <instance_id>`, and types in each answer the child wrote on paper. The system accepts all answers, confirms them, and automatically scores the worksheet.

**Why this priority**: This is the core value proposition — fast, simple answer entry that replaces the broken OCR pipeline. Without this, no scoring can happen.

**Independent Test**: Can be fully tested by generating a worksheet, running `kumon submit` with known answers, and verifying the score output matches expected results.

**Acceptance Scenarios**:

1. **Given** a previously generated worksheet with instance_id "abc123", **When** the parent runs `kumon submit abc123` and enters answers for all exercises, **Then** the system stores all answers linked to that worksheet instance and displays a confirmation prompt.
2. **Given** the parent has entered all answers and sees the confirmation prompt, **When** the parent confirms submission, **Then** scoring runs automatically and results are displayed in Greek-friendly output.
3. **Given** a worksheet with 15 exercises, **When** the parent enters answers one by one, **Then** the system prompts for each answer sequentially showing the exercise number/context.
4. **Given** the parent wants to enter all answers at once, **When** they provide answers as a comma-separated list, **Then** the system accepts and maps them to the correct exercises in order.

---

### User Story 2 - Review and Correct Answers Before Submission (Priority: P2)

After entering answers, the parent notices they misread one of the child's answers. Before confirming, they want to review what they entered and fix the mistake.

**Why this priority**: Typos and misreads are inevitable when transcribing handwritten answers. Correction before scoring prevents false failure records.

**Independent Test**: Can be tested by entering answers, requesting a review, changing one answer, and verifying the corrected answer is used for scoring.

**Acceptance Scenarios**:

1. **Given** the parent has entered all answers, **When** the system shows the confirmation prompt, **Then** a summary of all entered answers is displayed for review.
2. **Given** the parent sees the answer summary, **When** they indicate answer #7 needs correction, **Then** the system allows them to re-enter just that answer.
3. **Given** the parent has corrected an answer, **When** they confirm submission, **Then** the corrected answer (not the original) is stored and scored.

---

### User Story 3 - Record Completion Timing (Priority: P3)

The parent timed how long the child took to complete the worksheet and wants to record this alongside the answers for tracking progress over time.

**Why this priority**: Timing data enriches mastery tracking but is not required for core scoring functionality.

**Independent Test**: Can be tested by submitting answers with a timing value and verifying it appears in the stored submission record.

**Acceptance Scenarios**:

1. **Given** the parent is submitting answers, **When** they optionally provide timing (e.g., `--time 12m`), **Then** the duration is stored with the submission record.
2. **Given** the parent does not provide timing, **When** they submit answers, **Then** the submission succeeds without timing data (field is optional).

---

### Edge Cases

- What happens when the parent provides an invalid or non-existent instance_id?
- What happens when the parent enters fewer answers than the worksheet has exercises?
- What happens when the parent enters more answers than expected?
- How does the system handle non-numeric answers for math exercises (e.g., typos like "1o" instead of "10")?
- What happens if the parent cancels mid-entry (Ctrl+C)?
- What happens if a submission already exists for this worksheet instance?
- How does the system handle answers with Greek characters or special math notation?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the parent to select a worksheet by instance_id via `kumon submit <instance_id>`
- **FR-002**: System MUST validate that the provided instance_id corresponds to an existing, previously generated worksheet
- **FR-003**: System MUST support sequential one-by-one answer entry with clear prompts showing exercise number
- **FR-004**: System MUST support bulk answer entry (comma-separated or space-separated list)
- **FR-005**: System MUST display a complete summary of entered answers before requiring confirmation
- **FR-006**: System MUST allow the parent to correct any individual answer before final confirmation
- **FR-007**: System MUST store confirmed answers linked to the worksheet instance with a timestamp
- **FR-008**: System MUST trigger deterministic scoring automatically upon confirmation
- **FR-009**: System MUST display scoring results with Greek-friendly output (Greek labels, proper character encoding)
- **FR-010**: System MUST optionally accept a timing/duration parameter for the worksheet completion
- **FR-011**: System MUST maintain a full audit trail: worksheet → submission (manual answers) → score
- **FR-012**: System MUST reject submission if a confirmed submission already exists for the instance (prevent duplicates)
- **FR-013**: System MUST gracefully handle partial entry (allow the parent to resume or restart if interrupted)
- **FR-014**: System MUST NOT require any image upload, OCR processing, or vision model capabilities

### Key Entities

- **Worksheet Instance**: A previously generated worksheet identified by instance_id, containing the exercises and their correct answers
- **Submission**: A record of the parent's manually entered answers for a specific worksheet instance, including optional timing and confirmation status
- **Score**: The deterministic scoring result computed by comparing submitted answers against correct answers, linked to the submission

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parent can complete full answer entry for a 20-exercise worksheet in under 2 minutes
- **SC-002**: Scoring results display within 1 second of confirmation
- **SC-003**: 100% of submitted answers are accurately stored and correctly linked to their worksheet instance
- **SC-004**: Parent can correct any entered answer in under 10 seconds
- **SC-005**: The complete workflow (select worksheet → enter answers → review → confirm → see score) completes in under 3 minutes for a typical 15-exercise worksheet
- **SC-006**: Zero external service dependencies required — works fully offline on local device

## Assumptions

- Worksheets have already been generated and stored locally with unique instance_ids before submission occurs
- The parent has access to the child's completed paper worksheet and can read the handwritten answers
- Answers are primarily numeric (integers, decimals, fractions) appropriate for a 10-year-old's math level
- The correct answers for each exercise are stored with the worksheet instance at generation time
- The system runs on a resource-constrained device that cannot support OCR or vision model processing
- Greek-friendly output means Greek-language labels and messages, not that answers themselves are in Greek
- CLI is the primary interface; web UI is a future enhancement outside this spec's scope
- A single parent user operates the system (no multi-user concurrency concerns)


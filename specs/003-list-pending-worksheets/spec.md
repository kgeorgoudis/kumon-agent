# Feature Specification: List Pending Worksheets

**Feature Branch**: `003-list-pending-worksheets`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "As a parent I want to be able to list not-submitted worksheets so that I can get the worksheet id and submit the answers after restarting my terminal (lose the id from `kumon generate` command)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List Unsubmitted Worksheets (Priority: P1)

A parent generates a worksheet with `kumon generate`, prints it, and the child solves it on paper. Later — possibly after restarting the terminal or closing the session — the parent wants to submit the answers. They no longer have the worksheet instance ID that was displayed during generation. The parent runs `kumon pending` (or `kumon list-pending`) and sees a table of all worksheets that have not yet been submitted. The table shows enough information (date, skill, exercise count, and full/short ID) for the parent to identify the correct worksheet and copy the ID into `kumon submit <id>`.

**Why this priority**: This is the core and only use case for the feature. Without it, the parent must dig through the database or `kumon history` output and manually cross-reference which worksheets already have submissions. This command removes that friction entirely.

**Independent Test**: Can be fully tested by generating one or more worksheets, submitting answers for some of them, and verifying that `kumon pending` shows only the unsubmitted ones with correct details.

**Acceptance Scenarios**:

1. **Given** two worksheets have been generated and neither has been submitted, **When** the parent runs `kumon pending`, **Then** both worksheets appear in the output table with date, skill name, exercise count, and a copyable worksheet ID.
2. **Given** three worksheets exist and one has a confirmed submission, **When** the parent runs `kumon pending`, **Then** only the two unsubmitted worksheets appear.
3. **Given** no worksheets have been generated, **When** the parent runs `kumon pending`, **Then** a friendly Greek message is displayed indicating there are no pending worksheets.
4. **Given** a worksheet has a draft (in-progress) submission that was never confirmed, **When** the parent runs `kumon pending`, **Then** that worksheet still appears in the pending list (since it has not been scored).

---

### User Story 2 - Filter Pending Worksheets by Child (Priority: P2)

A parent with multiple child profiles wants to see only the pending worksheets for a specific child. They run `kumon pending --child "Ελένη"` and the list is filtered to show only that child's unsubmitted worksheets.

**Why this priority**: Multi-child support is secondary to the basic list functionality but important for households with more than one child using the system.

**Independent Test**: Can be tested by generating worksheets for two different child profiles, then verifying that filtering by child name returns only the correct subset.

**Acceptance Scenarios**:

1. **Given** worksheets exist for two children, **When** the parent runs `kumon pending --child "Ελένη"`, **Then** only worksheets belonging to Ελένη are displayed.
2. **Given** worksheets exist but none for the specified child, **When** the parent runs `kumon pending --child "Κώστας"`, **Then** a message indicates no pending worksheets for that child.

---

### Edge Cases

- What happens when the database is empty (no worksheets at all)? → Show a friendly Greek message.
- What happens when all generated worksheets have been submitted? → Show a message indicating no pending worksheets remain.
- What happens when a worksheet has a cancelled submission? → It should appear as pending (cancelled submissions do not count as completed).
- What happens when a worksheet has a draft submission? → It should appear as pending with a visual indicator that a draft exists.
- How are worksheets with no child_id (transient profile) handled? → They should still appear in the unfiltered list.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a CLI command that lists all worksheets without a confirmed submission.
- **FR-002**: System MUST display each pending worksheet's creation date, skill name (Greek), exercise count, and a copyable instance ID.
- **FR-003**: System MUST support filtering the pending list by child name via `--child` option.
- **FR-004**: System MUST display a friendly Greek message when no pending worksheets are found.
- **FR-005**: System MUST treat worksheets with only draft or cancelled submissions as pending (not submitted).
- **FR-006**: System MUST show the full instance ID (not truncated) so the parent can copy-paste it into `kumon submit`.
- **FR-007**: System MUST sort pending worksheets by creation date, most recent first.

### Key Entities

- **WorksheetInstance**: The generated worksheet. Key attributes: instance_id, child_id, micro_skill_id, title_el, exercises (count), created_at.
- **ManualSubmission**: The submission record. A worksheet is "pending" if it has no ManualSubmission with status=CONFIRMED linked to it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A parent can retrieve the ID of any unsubmitted worksheet within 5 seconds using a single command.
- **SC-002**: The pending list accurately reflects submission status — 100% of confirmed-submitted worksheets are excluded, 100% of unsubmitted worksheets are included.
- **SC-003**: The command output is readable and self-explanatory in Greek without consulting documentation.
- **SC-004**: The parent can copy the displayed ID directly into `kumon submit <id>` without modification.

## Assumptions

- The existing `kumon history` command shows all worksheets but does not distinguish between submitted and unsubmitted ones — this new command fills that gap.
- The database already stores both WorksheetInstance and ManualSubmission records, making it possible to determine submission status via a query.
- The command name will be `pending` (short and intuitive). An alias `list-pending` is not required but may be added later.
- The feature is CLI-only for now; web UI integration is out of scope.
- The output format follows the same Rich table styling used by existing commands (`history`, `list-skills`).


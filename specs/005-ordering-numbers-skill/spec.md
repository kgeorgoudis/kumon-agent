# Feature Specification: Ordering Numbers Skill

**Feature Branch**: `005-ordering-numbers-skill`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Implement ordering_numbers kumon skill — currently listed in the skill catalogue but raises ValueError when generating a worksheet because no exercise generator exists."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Ordering Numbers Worksheet (Priority: P1)

A parent selects the "ordering_numbers" micro-skill and generates a worksheet. The system produces a printable worksheet containing exercises where the child must arrange a set of numbers in ascending or descending order (up to 1000).

**Why this priority**: This is the core gap — the skill is advertised but cannot produce a worksheet. Fixing this unblocks the entire ordering_numbers learning loop.

**Independent Test**: Can be fully tested by running `uv run kumon generate --skill ordering_numbers` and verifying a printable worksheet with correct answer key is produced.

**Acceptance Scenarios**:

1. **Given** the system has the ordering_numbers micro-skill registered, **When** a parent generates a worksheet for ordering_numbers, **Then** the system produces a worksheet with the configured number of exercises (default 15) and a matching answer key.
2. **Given** a seed value is provided, **When** the same worksheet is generated twice with the same seed, **Then** both worksheets contain identical exercises.
3. **Given** a generated ordering_numbers worksheet, **When** the parent prints it, **Then** each exercise clearly presents a set of numbers and instructs the child to write them in the correct order.

---

### User Story 2 - Score Ordering Numbers Submission (Priority: P2)

After a child completes an ordering_numbers worksheet on paper, the parent uploads it and the scoring engine correctly evaluates whether the child placed numbers in the right order.

**Why this priority**: Without scoring, the learning loop cannot close. Scoring must handle the unique answer format (ordered sequence of numbers rather than a single numeric answer).

**Independent Test**: Can be tested by providing known child answers to an ordering_numbers worksheet and verifying the scoring engine returns correct/incorrect for each exercise.

**Acceptance Scenarios**:

1. **Given** a completed ordering_numbers worksheet with all answers correct, **When** the submission is scored, **Then** accuracy is 100%.
2. **Given** a completed ordering_numbers worksheet with some answers in wrong order, **When** the submission is scored, **Then** only the correctly ordered exercises are marked correct.

---

### User Story 3 - Progression Integration (Priority: P3)

The ordering_numbers skill participates in the normal mastery and progression loop — accuracy is tracked and the planner can advance, hold, or step back based on performance.

**Why this priority**: Progression integration ensures ordering_numbers behaves like any other micro-skill in the system.

**Independent Test**: Can be tested by simulating multiple worksheet submissions for ordering_numbers and verifying the mastery state transitions follow the standard progression rules.

**Acceptance Scenarios**:

1. **Given** a child achieves ≥90% accuracy on 3 consecutive ordering_numbers worksheets, **When** the planner runs, **Then** the child is advanced to the next skill.

---

### Edge Cases

- What happens when all numbers in a set are the same? (Degenerate case — system must ensure distinct numbers in each exercise.)
- How does the system handle the child writing numbers with different spacing or formatting? (OCR/scoring must be tolerant of whitespace variations.)
- What if the direction instruction (ascending vs descending) is ambiguous? (Each exercise must clearly state the required direction in Greek.)
- What range of numbers is appropriate for the child's level? (Numbers up to 1000, with configurable difficulty progression within that range.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate ordering_numbers exercises where each exercise presents a set of 4–6 numbers and asks the child to arrange them in ascending or descending order.
- **FR-002**: System MUST ensure all numbers within a single exercise are distinct.
- **FR-003**: System MUST generate numbers in a range appropriate to difficulty level 2 (up to 1000, with a mix of 1-digit, 2-digit, and 3-digit numbers).
- **FR-004**: System MUST produce a deterministic sequence of exercises given the same seed value.
- **FR-005**: System MUST include both ascending ("Βάλε σε σειρά από το μικρότερο στο μεγαλύτερο") and descending ("Βάλε σε σειρά από το μεγαλύτερο στο μικρότερο") exercises, with a roughly even mix.
- **FR-006**: System MUST produce an answer key that shows the correctly ordered sequence for each exercise.
- **FR-007**: System MUST register the ordering_numbers generator in the math engine so that `generate_exercises(MicroSkillId.ORDERING_NUMBERS, ...)` succeeds without error.
- **FR-008**: System MUST support scoring of ordering_numbers answers by comparing the child's sequence against the correct sequence.
- **FR-009**: System MUST render ordering_numbers exercises in the existing worksheet HTML/PDF template with clear Greek instructions.

### Key Entities

- **Exercise (ordering variant)**: Contains a set of numbers, an ordering direction (ascending/descending), and the correct answer (the sorted sequence).
- **MicroSkillId.ORDERING_NUMBERS**: Already exists in the enum and knowledge base; needs a corresponding generator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parent can generate an ordering_numbers worksheet in under 10 seconds via CLI or web UI.
- **SC-002**: 100% of generated exercises have verifiably correct answer keys (deterministic, testable by code).
- **SC-003**: Scoring correctly identifies right and wrong answers for ordering exercises with 100% accuracy on known test fixtures.
- **SC-004**: The ordering_numbers skill integrates seamlessly with existing progression rules — no special-case logic required in the planner.

## Assumptions

- The existing Exercise model can accommodate ordering-type exercises (which have a list of numbers as answer rather than a single number). If not, a minor model extension is acceptable.
- Ordering exercises use a comma-separated or space-separated format for both problem display and answer representation.
- Numbers up to 1000 are age-appropriate for a 10-year-old child (aligns with Greek curriculum for Δ' Δημοτικού).
- OCR scoring for ordering exercises will compare the sequence of extracted numbers against the answer key sequence; partial credit is not given (the entire sequence must be correct for the exercise to be marked correct).
- The worksheet template can render ordering exercises without major template changes — each exercise shows a set of numbers and a direction instruction.


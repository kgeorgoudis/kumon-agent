# AGENTS.md

## Project

Kumon-style math practice agent for a 10-year-old child in Greece, focused on deliberate practice through short printed worksheets, paper-based solving, scan/photo ingestion, evaluation, and generation of the next worksheet.

The product is **not** a general chatbot. It is a structured tutoring workflow with deterministic scoring, mastery tracking, and tightly bounded AI assistance.

## Product Goal

Build a local-first tutoring system that helps a child improve math fluency and understanding through:

- Short, incremental worksheets.
- Immediate evaluation of completed paper exercises.
- Detection of recurring mistake patterns.
- Controlled progression to the next appropriate worksheet.
- Parent-friendly review and printing workflow.
- Greek-first content and UI.

## Primary Users

- Parent/operator: uploads solved worksheets, reviews OCR, prints next worksheet, checks progress.
- Child: solves exercises on paper; minimal direct UI interaction.
- Developer/operator: maintains prompts, templates, OCR pipeline, progression logic, and reports.

## Non-Goals

- Do not build an open-ended conversational tutor as the main UX.
- Do not let the LLM invent arithmetic answers.
- Do not make the model the source of truth for scoring.
- Do not optimize for flashy UI before the worksheet loop works reliably.
- Do not depend on cloud-only services unless explicitly enabled later.

## Core Principles

1. Deterministic before agentic.
2. Arithmetic truth must come from code, not the LLM.
3. The LLM may explain, classify ambiguous mistakes, summarize, and draft parent notes.
4. Every progression decision must be inspectable.
5. The parent must be able to override any automated decision.
6. Paper workflow is the center of the product.
7. Keep assignments short and incremental.
8. Default language is Greek.
9. Local-first architecture is preferred.
10. Shared domain logic must power both CLI and web UI.

## Suggested Architecture

### Preferred v1 stack

- Python
- FastAPI for local web UI and API
- LangGraph only where stateful orchestration is genuinely useful
- SQLite for local persistence in v1
- Jinja2 templates or similarly simple server-rendered UI
- PDF/HTML worksheet generation from templates
- OCR pipeline for worksheet images/PDFs
- CLI for developer and batch workflows

### Optional later stack evolution

- Rust sidecar or library for selected high-confidence deterministic components
- Postgres instead of SQLite
- More advanced OCR or vision model pipeline
- Optional local LLM via Ollama or LM Studio

## UI Strategy

Build two entry points over one shared core:

1. Web UI for parent workflow.
2. CLI for development, batch generation, debugging, exports, and maintenance.

### Web UI priorities

The v1 screens should be:

- Dashboard
- Generate worksheet
- Upload solved worksheet
- OCR review/correction
- Results and diagnosis
- History
- Child profile/settings

### CLI priorities

The CLI should support:

- generate worksheet
- score uploaded worksheet
- inspect OCR output
- re-run planning logic
- export history
- run local evaluation suite

## Agent Boundary

Use agents only where they add value.

### Good uses of the LLM/agent

- Explain a mistake in simple Greek.
- Summarize a worksheet result for the parent.
- Suggest whether an error pattern looks conceptual or careless.
- Draft next-step rationale.
- Help classify ambiguous OCR or handwritten edge cases for review.

### Bad uses of the LLM/agent

- Compute arithmetic answers as the source of truth.
- Decide progression without explicit rules and visible state.
- Generate unrestricted teaching advice with no grounding in worksheet history.
- Replace deterministic parsing/scoring where templates are known.

## Domain Model

### Core entities

- ChildProfile
- Skill
- MicroSkill
- WorksheetTemplate
- WorksheetInstance
- WorksheetSubmission
- OCRResult
- ScoreResult
- ErrorPattern
- MasteryState
- ProgressDecision
- ParentNote

### Example ChildProfile fields

- child_id
- display_name
- age
- grade_level
- locale
- language
- preferred_sheet_length
- timing_enabled
- review_mix_ratio
- notes

### Example Skill hierarchy

- Number sense
- Addition
- Subtraction
- Multiplication
- Division
- Fractions
- Word problems
- Place value

### Example MicroSkills

- Half and double
- Addition with carrying
- Subtraction with borrowing
- Multiplication facts 2-5
- Multiplication facts 6-9
- Division as inverse of multiplication
- Fractions with same denominator
- Compare simple fractions
- Two-step word problems

## Workflow

### Main learning loop

1. Parent generates worksheet.
2. Worksheet is printed.
3. Child solves on paper.
4. Parent uploads image or PDF.
5. OCR extracts answers.
6. Parent reviews low-confidence fields.
7. Scoring engine evaluates correctness.
8. Error analyzer detects patterns.
9. Mastery engine updates skill state.
10. Planner chooses next worksheet.
11. System generates printable next worksheet and parent summary.

### Recovery loop

If performance drops or a repeated misconception appears:

1. Detect unstable micro-skill.
2. Step down one level or reduce complexity.
3. Generate focused correction sheet.
4. Re-test with a shorter follow-up sheet.

## Progression Rules

All progression rules must be deterministic, configurable, and testable.

### Suggested defaults

- Advance when recent accuracy is consistently high and the child is stable across multiple sheets.
- Stay on the same level with variation when accuracy is moderate.
- Step back or switch to concept-repair mode when repeated misconceptions appear.
- Speed should matter only after accuracy becomes reliable.

### Requirements

- Rules must be encoded in code, not just prompts.
- Every decision must produce a machine-readable explanation.
- Parent override must always be available.

## OCR and Review

OCR is expected to be imperfect. Design for reviewability.

### Requirements

- Keep original submission image.
- Store extracted text/boxes/confidence.
- Mark ambiguous cells clearly.
- Support manual correction before scoring.
- Record whether a value came from OCR or manual correction.
- Make rescoring idempotent after correction.

## Worksheet Generation

Worksheet generation should be template-driven.

### Supported worksheet types

- Drill
- Mixed review
- Correction sheet
- Timed fluency sheet
- Concept reinforcement sheet
- Word problem sheet

### Requirements

- Printable output must be clean and child-friendly.
- Use Greek wording by default.
- Exercise difficulty must progress gradually.
- Mixed sheets should combine target skill and prior review.
- Answer keys must be produced separately.

## Data and Persistence

Persist all core events locally.

### Minimum data to store

- Generated worksheets
- Submission artifacts
- OCR results
- Scoring results
- Progress decisions
- Parent overrides
- Skill mastery snapshots
- Audit trail for explanation/debugging

### Rules

- Never lose the linkage between worksheet, submission, and decision.
- Prefer append-only event history where practical.
- Avoid hidden mutable state.

## Spec-Driven Development Expectations

This repository should be operated in a spec-driven way.

### Before implementing a feature

Create or update specs for:

- Goal
- User flow
- Inputs/outputs
- Domain entities
- Constraints
- Acceptance criteria
- Failure modes
- Test cases

### Recommended spec areas

- worksheet-generation
- worksheet-ingestion
- OCR-review
- scoring-engine
- mastery-engine
- progression-planner
- parent-dashboard
- CLI
- localization-el-GR

## Coding Agent Instructions

When working in this repository, the coding agent must follow these rules.

### General behavior

- Read existing specs before changing code.
- Prefer small, reviewable changes.
- Keep business logic separated from transport and UI layers.
- Ask for clarification when a requested change conflicts with product goals.
- Avoid introducing unnecessary frameworks.

### Architecture rules

- Put deterministic domain logic in plain Python modules.
- Keep FastAPI handlers thin.
- Keep LangGraph orchestration isolated from core scoring and mastery logic.
- Ensure CLI and web routes call the same service layer.
- Avoid coupling prompt logic to persistence details.

### Testing rules

- Add tests for all progression logic changes.
- Add fixture-based tests for worksheet parsing and scoring.
- Add regression tests for past OCR/scoring bugs.
- Test Greek localization paths.
- Prefer deterministic tests over prompt-only expectations.

### Prompt rules

- Prompts must be versioned.
- Prompts must be narrow and role-specific.
- Prompts must not be the only place where business rules exist.
- Prompt outputs should be structured JSON whenever possible.

### Safety rules

- Never expose child data unnecessarily.
- Default to local processing.
- Avoid sending worksheet images to remote APIs unless explicitly configured.
- Do not store secrets in code or prompts.

## Suggested Repository Layout

```text
.
├── AGENTS.md
├── specs/
│   ├── worksheet-generation/
│   ├── worksheet-ingestion/
│   ├── scoring-engine/
│   ├── mastery-engine/
│   ├── progression-planner/
│   ├── parent-dashboard/
│   └── localization-el-GR/
├── app/
│   ├── api/
│   ├── web/
│   ├── cli/
│   ├── domain/
│   ├── services/
│   ├── agents/
│   ├── prompts/
│   ├── templates/
│   ├── persistence/
│   └── tests/
├── data/
├── output/
└── README.md
```

## Initial Milestones

### Milestone 1

- Define specs.
- Implement worksheet template model.
- Generate printable worksheets and answer keys.
- Add CLI entry point.

### Milestone 2

- Add upload and OCR ingestion.
- Add OCR review screen.
- Add deterministic scoring engine.

### Milestone 3

- Add mastery tracking.
- Add progression planner.
- Add parent dashboard and history.

### Milestone 4

- Add LLM-generated Greek explanations and parent notes.
- Add evaluation harness for planner quality.

## Acceptance Criteria for v1

The system is useful when:

- A parent can generate a worksheet in under one minute.
- A solved worksheet can be uploaded and reviewed quickly.
- Scoring is deterministic and auditable.
- The app suggests a sensible next worksheet.
- The full loop works locally.
- Greek-first output is readable and child-appropriate.

## Definition of Done

A feature is done only when:

- Spec exists or is updated.
- Domain behavior is implemented.
- Tests cover success and failure paths.
- UI/CLI entry point is usable.
- Logs/errors are understandable.
- The feature fits the paper-based tutoring workflow.
- Any agent behavior is bounded, inspectable, and optional where appropriate.

## Build Priorities

When in doubt, prioritize in this order:

1. Correct worksheet generation.
2. Reliable ingestion and scoring.
3. Clear progression logic.
4. Parent review UX.
5. LLM assistance.
6. Visual polish.

## Final Reminder to Coding Agents

This project succeeds by being reliable, inspectable, local-first, and helpful to a real parent and child. Favor boring correctness over impressive autonomy.

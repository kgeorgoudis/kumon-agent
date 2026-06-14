<!--
Sync Impact Report
==================
- Version change: 0.0.0 → 1.0.0
- Modified principles: N/A (initial creation)
- Added sections:
  - Core Principles (10 principles)
  - Technology & Architecture Constraints
  - Development Workflow
  - Governance
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ No changes needed (generic)
  - .specify/templates/spec-template.md ✅ No changes needed (generic)
  - .specify/templates/tasks-template.md ✅ No changes needed (generic)
- Follow-up TODOs: None
-->

# Kumon Agent Constitution

## Core Principles

### I. Deterministic Before Agentic

All arithmetic evaluation, scoring, progression decisions, and mastery
tracking MUST be implemented as deterministic Python code. The LLM MUST
NOT be the source of truth for any computation or decision that can be
expressed as a rule. Agent orchestration (LangGraph) is permitted only
for tasks where statefulness and ambiguity genuinely require it (e.g.,
classifying handwriting, explaining mistakes in Greek, summarizing
results for the parent).

### II. Arithmetic Truth From Code

Every mathematical answer, score calculation, and correctness check MUST
be computed by Python code—never by the LLM. The scoring engine MUST
produce identical results given identical inputs regardless of whether an
LLM is available. Unit tests MUST cover all arithmetic paths.

### III. Inspectable Progression

Every progression decision (advance, stay, step-back) MUST produce a
machine-readable explanation that a parent can review. Decisions MUST
reference concrete data: accuracy percentages, error counts, micro-skill
identifiers. No hidden state transitions are permitted.

### IV. Parent Override Authority

The parent MUST be able to override any automated decision at any point:
skip a worksheet, force a level change, mark an OCR result as correct,
or pause the system entirely. Overrides MUST be recorded in the audit
trail with timestamp and reason.

### V. Paper Workflow First

The primary user experience is: generate → print → solve on paper →
photograph/scan → review → score → plan next. Every feature MUST be
evaluated against whether it supports or disrupts this physical loop.
Digital-only interactions are secondary.

### VI. Short and Incremental Assignments

Worksheets MUST be short (configurable, default 10–15 exercises). Each
worksheet MUST target one primary micro-skill plus an optional review
mix. Difficulty progression MUST be gradual—never skip more than one
complexity step between consecutive worksheets.

### VII. Greek-First Content and UI

All child-facing content (exercises, instructions, feedback) MUST be in
Greek by default. Parent-facing UI MUST default to Greek. Internal code,
logs, comments, and developer documentation MUST be in English. The
system MUST support locale configuration for future expansion.

### VIII. Local-First Architecture

The system MUST function fully offline once dependencies are installed.
The LLM runs locally (currently Qwen3-8B-MLX-4bit at
`http://127.0.0.1:8000/v1`). No child data MUST leave the local machine
unless explicitly configured by the parent. SQLite is the default
persistence layer.

### IX. Shared Domain Logic

All business logic (scoring, mastery, progression, worksheet generation)
MUST reside in plain Python domain modules. Both the CLI and the web UI
(FastAPI) MUST call the same service layer. Duplication of domain logic
across entry points is prohibited.

### X. In-App Documentation

Because the operator is not a Kumon expert or teacher, the application
MUST embed contextual documentation: explanations of the Kumon method,
micro-skill definitions, progression rationale, and worksheet type
descriptions. This documentation MUST be accessible from both the web UI
(help pages/tooltips) and the CLI (`--help`, `explain` subcommands), not
only in README files.

## Technology & Architecture Constraints

- **Language**: Python ≥ 3.12, managed with Astral `uv`.
- **Framework**: FastAPI (web/API), LangGraph (agent orchestration where
  justified), Typer or Click (CLI).
- **LLM**: Local inference via OpenAI-compatible endpoint at
  `http://127.0.0.1:8000/v1`, model `Qwen3-8B-MLX-4bit`. No cloud LLM
  calls unless explicitly enabled.
- **Persistence**: SQLite (v1). Append-only event history preferred.
- **Templating**: Jinja2 for worksheet and UI rendering.
- **Testing**: pytest. Deterministic tests for all domain logic.
  Fixture-based tests for OCR and scoring. Greek locale coverage.
- **Output**: PDF/HTML worksheets, printable and child-friendly.
- **OCR**: Pipeline for handwritten worksheet ingestion; designed for
  imperfect results with human review step.
- **Package layout**: Single `app/` package with sub-modules (`domain/`,
  `services/`, `api/`, `web/`, `cli/`, `agents/`, `prompts/`,
  `templates/`, `persistence/`, `tests/`).

## Development Workflow

- **Spec-driven**: Every feature MUST have a specification before
  implementation begins. Specs live in `specs/`.
- **Small changes**: Prefer small, reviewable increments over large
  refactors.
- **Test discipline**: All progression and scoring logic changes MUST
  have tests. Regression tests MUST be added for past bugs.
- **Prompt versioning**: All LLM prompts MUST be versioned files in
  `app/prompts/`. Prompts MUST output structured JSON. Prompts MUST NOT
  be the sole location of business rules.
- **Safety**: No child data in logs or prompts sent externally. No
  secrets in code. Default to local processing.
- **Audit trail**: Every worksheet generation, submission, score, and
  progression decision MUST be persisted with full linkage.

## Governance

- This constitution is the highest-authority document for development
  decisions in this repository. It supersedes ad-hoc preferences.
- Amendments require: (1) a written proposal describing the change and
  rationale, (2) version bump per semantic versioning, (3) updated
  Sync Impact Report.
- Version policy: MAJOR for principle removal/redefinition, MINOR for
  new principles or material expansion, PATCH for clarifications.
- Compliance review: Every PR or code change MUST be consistent with
  these principles. Violations MUST be justified in a Complexity
  Tracking table (see plan template).
- The `AGENTS.md` file provides expanded guidance and is subordinate
  to this constitution. In case of conflict, this constitution wins.

**Version**: 1.0.0 | **Ratified**: 2026-06-14 | **Last Amended**: 2026-06-14

# Feature Specification: LangGraph Agentic Architecture

**Feature Branch**: `007-langgraph-agent-architecture`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "I want to re-shape the project and include Langgraph into the code, so that the project is built following the agentic principles and structure of that framework."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified agentic tutor layer for all LLM tasks (Priority: P1)

As the maintainer, I want every language task the system performs — recommending the
next worksheet, reviewing a scored worksheet, and narrating a child's progress — to
run through a single, stateful agent orchestration layer instead of ad-hoc, one-off
LLM calls scattered across services. This makes the "Kumon Tutor" behave as one
coherent agent with explicit state, explicit steps, and explicit tools.

**Why this priority**: This is the core of the request — re-shaping the project around
agentic principles. Without a unified orchestration layer, every other improvement
(inspectability, graceful degradation, future conversational features) has no foundation.
Delivering just this slice already produces a working, demonstrable agentic tutor.

**Independent Test**: Run `kumon progress --child "Ελένη"` on a profile with scored
worksheets. The narrative and next-step suggestions are produced by the agent
orchestration layer, the output is identical in meaning to the prior implementation,
and the run is reproducible. Verifiable by inspecting that the tutor output is generated
through the new layer and that existing progress tests still pass.

**Acceptance Scenarios**:

1. **Given** a child with several scored worksheets, **When** the parent requests a
   progress report, **Then** the system produces a Greek narrative plus next-step
   suggestions through the agent layer, grounded only in the deterministic scored data.
2. **Given** a freshly scored worksheet, **When** the parent requests a review, **Then**
   the agent layer classifies mistakes (e.g., careless vs. conceptual) and frames
   encouraging Greek guidance without recomputing any score.
3. **Given** a request for the next worksheet, **When** the agent produces planning
   advice, **Then** the suggestion respects incremental progression (never skipping more
   than one complexity step) and is expressed as a suggestion the parent can override.

---

### User Story 2 - Deterministic truth stays code-owned (Priority: P1)

As the maintainer, I want the agent layer to call deterministic Python logic as "tools"
for every fact it uses — scores, accuracy percentages, mastery state, skill hierarchy —
so that the agent reasons over trusted data and never invents or recomputes arithmetic.

**Why this priority**: The constitution mandates that arithmetic and scoring truth remain
code-owned. Adopting an agent framework must not weaken this guarantee. This story is
inseparable from P1: an agentic layer that could fabricate scores would be a regression.

**Independent Test**: With the LLM endpoint pointed at a stubbed/mock model that returns
deliberately wrong numbers, the reported scores, accuracy, and correctness still match
the deterministic engine exactly. Verifiable by a test that confirms no score value in
final output originates from the model.

**Acceptance Scenarios**:

1. **Given** a scored worksheet, **When** the agent narrates results, **Then** every
   numeric claim (correct count, accuracy, trend) equals the deterministic computation.
2. **Given** a model that returns inconsistent or malformed numbers, **When** the agent
   runs, **Then** deterministic values are used and the model's numeric claims are ignored.

---

### User Story 3 - Graceful degradation when the model is unavailable (Priority: P2)

As a parent working offline or with the local model stopped, I want every command to keep
working and return the deterministic results, with the tutor narrative simply omitted,
so the paper workflow is never blocked by the agent layer.

**Why this priority**: Local-first operation is a core principle. The agentic refactor
must preserve the existing graceful-degradation behavior already present in the progress
flow. It is P2 because P1 must exist first, but it gates release.

**Independent Test**: Stop the local model, run `kumon progress` and a worksheet review.
Each command exits successfully, shows deterministic metrics, and clearly indicates that
the tutor narrative was unavailable. Verifiable offline with no network.

**Acceptance Scenarios**:

1. **Given** the model endpoint is unreachable, **When** the parent runs progress or
   review, **Then** the command succeeds and shows deterministic data with a "narrative
   unavailable" indication.
2. **Given** the model times out mid-run, **When** the agent layer detects the failure,
   **Then** it degrades to deterministic-only output rather than erroring out.

---

### User Story 4 - Inspectable, versioned agent behavior (Priority: P3)

As the maintainer, I want the agent's steps, persona, and prompts to be explicit,
versioned, and traceable, so I can review what the tutor did and why, and reproduce it.

**Why this priority**: Inspectability and prompt versioning are constitutional
requirements and make the system maintainable, but the system can ship a first agentic
version before full tracing polish. Hence P3.

**Independent Test**: Trigger any tutor task and confirm that the persona prompt used is a
versioned artifact, the sequence of agent steps is recorded, and the same inputs produce
the same step sequence. Verifiable by inspecting the recorded trace/audit for one run.

**Acceptance Scenarios**:

1. **Given** any tutor task runs, **When** the maintainer inspects the run, **Then** the
   persona/prompt version and the ordered steps the agent took are visible.
2. **Given** identical inputs, **When** the task is run twice, **Then** the agent follows
   the same deterministic control flow (model wording may differ, structure does not).

---

### Edge Cases

- What happens when a tutor task receives an empty history (no scored worksheets)? The
  agent must return a safe, deterministic "not enough data yet" outcome in Greek without
  calling the model for fabricated encouragement.
- How does the system handle a malformed or non-JSON model response? It must treat the
  response as a degraded/unavailable narrative and fall back to deterministic output.
- What happens when a tool (deterministic function) raises an error mid-run? The agent
  must surface a clear failure for that branch without corrupting the audit trail.
- How does the system behave if a parent overrides a suggestion the agent produced? The
  override must take precedence and be recorded, with the agent never re-asserting control.
- What happens to existing CLI and web entry points during the refactor? They must
  continue to call the same shared service layer and produce equivalent results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single agent orchestration layer that handles all
  LLM-driven tutor responsibilities: worksheet planning advice, worksheet review, and
  progress reporting.
- **FR-002**: The agent layer MUST be structured around explicit agentic concepts — a
  shared task state, discrete processing steps, and callable deterministic tools — rather
  than ad-hoc single-shot model calls.
- **FR-003**: All existing user-facing commands and pages (worksheet generation,
  submission/scoring, pending, history, progress) MUST continue to work with equivalent
  behavior and output after the refactor.
- **FR-004**: The CLI and the web/API entry points MUST both invoke the same shared
  service layer, with no duplication of tutor or domain logic across entry points.
- **FR-005**: The agent layer MUST obtain every factual value (scores, accuracy, trends,
  mastery state, skill hierarchy) from deterministic Python logic and MUST NOT compute or
  alter any arithmetic or scoring result itself.
- **FR-006**: The agent layer MUST ignore any numeric or factual claim from the model that
  conflicts with deterministic data; deterministic values always win.
- **FR-007**: Every tutor task MUST degrade gracefully to deterministic-only output when
  the model is unavailable, slow, or returns an unusable response, without failing the
  command.
- **FR-008**: All tutor reasoning MUST operate under the Kumon Tutor Persona, encoded in
  versioned prompt artifacts rather than improvised per call.
- **FR-009**: Tutor recommendations MUST be expressed as suggestions the parent can accept
  or override, and parent overrides MUST take precedence and be recorded in the audit trail.
- **FR-010**: Worksheet planning advice produced by the agent MUST honor incremental
  progression, never suggesting a jump of more than one complexity step.
- **FR-011**: All child- and parent-facing tutor output MUST default to Greek; internal
  code, logs, and step names MUST be in English.
- **FR-012**: The agent layer MUST function fully offline against the locally configured
  model endpoint, with no required cloud calls.
- **FR-013**: Each tutor run MUST be inspectable: the persona/prompt version used and the
  ordered sequence of steps taken MUST be traceable for review.
- **FR-014**: The agent layer's control flow MUST be deterministic for identical inputs
  (same steps in the same order), even though model-generated wording may vary.
- **FR-015**: The refactor MUST preserve backward compatibility with existing stored data
  (profiles, worksheets, submissions, score snapshots) with no destructive migration.
- **FR-016**: The agent layer's behavior MUST be covered by automated tests that run
  offline using a stubbed/mock model, including the degradation path.

### Key Entities *(include if feature involves data)*

- **Tutor Task State**: The working context for one agent run. Holds the deterministic
  inputs (child, scored history, skill metadata), intermediate results, and the final
  tutor output. Carries no source-of-truth arithmetic of its own.
- **Tutor Step**: A discrete unit of work in the agent flow (e.g., "gather deterministic
  facts", "classify mistakes", "compose Greek narrative", "assemble suggestions"). Steps
  are ordered and named in English.
- **Deterministic Tool**: A callable wrapper over existing Python domain/service logic
  (scoring, progression, progress aggregation, skill hierarchy) that the agent invokes to
  obtain trusted facts.
- **Tutor Persona Prompt**: A versioned prompt artifact encoding the Kumon Tutor Persona
  and the grounding constraints for a given responsibility (planning, review, reporting).
- **Tutor Outcome**: The structured result of a run — deterministic metrics plus optional
  Greek narrative and override-able suggestions, with a flag indicating whether the
  narrative was produced or degraded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of LLM-driven tutor tasks (planning advice, worksheet review, progress
  reporting) are produced through the single agent orchestration layer, with zero remaining
  ad-hoc model-call paths in the service layer.
- **SC-002**: 100% of numeric values shown to parents (scores, accuracy, trends) match the
  deterministic engine exactly, even when the model returns conflicting numbers.
- **SC-003**: Every tutor command completes successfully with the model stopped, returning
  deterministic results and a clear "narrative unavailable" indication, in 100% of offline
  runs.
- **SC-004**: All existing automated tests pass after the refactor, and new tests cover the
  agent layer including the degradation path, with the full suite running offline.
- **SC-005**: A maintainer can identify, for any tutor run, the persona/prompt version and
  the ordered steps taken, in under 2 minutes without reading source code.
- **SC-006**: Identical inputs produce an identical sequence of agent steps across repeated
  runs (deterministic control flow), verified by automated test.
- **SC-007**: No existing stored data requires destructive migration; existing databases
  open and operate without manual intervention.

## Assumptions

- **Scope is a structural reshape plus foundation, not new end-user capabilities**: This
  feature re-routes the three existing tutor responsibilities through an agentic layer and
  preserves current user-facing behavior. New interactive/conversational tutoring modes
  are out of scope for this iteration and may build on this foundation later.
- **The local model and offline-first operation remain unchanged**: The agent layer targets
  the existing locally configured OpenAI-compatible endpoint; no cloud provider is introduced.
- **Deterministic domain and scoring logic remain authoritative**: Existing Python
  scoring/progression/aggregation logic is reused as tools and is not reimplemented inside
  the agent layer.
- **The manual paper workflow is primary**: generate → print → solve → manual submit →
  score → report; the agent layer supports, never blocks, this loop.
- **Prompts are versioned artifacts**: Persona and task prompts live as versioned files and
  output structured results, consistent with existing prompt-versioning practice.
- **Backward compatibility is required**: Existing profiles, worksheets, submissions, and
  score snapshots continue to work without migration.
- **Tests must run fully offline**: Agent-layer tests use a stubbed/mock model so the suite
  needs no network or running local model.
</content>


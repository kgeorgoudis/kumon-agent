# Research: Progress Summary

## Decision 1: Expose progress via `kumon progress` and `/progress`

- **Decision**: Add a top-level CLI command `kumon progress` and a web route `/progress`, both backed by one shared service.
- **Rationale**: Meets `FR-006` while enforcing Principle IX (shared domain logic).
- **Alternatives considered**:
  - Reuse `kumon history`: rejected because history is record listing, not report synthesis.
  - CLI-only v1: rejected because spec explicitly requires web and CLI exposure.

## Decision 2: Aggregate from confirmed manual submissions + score snapshots

- **Decision**: Build progress datasets from worksheets that have a confirmed `manual_submissions` record and matching `score_result_snapshots` entries.
- **Rationale**: Confirmed submissions are deterministic completion boundaries; avoids draft/cancelled noise.
- **Alternatives considered**:
  - Include draft submissions: rejected because they are incomplete and distort progress metrics.
  - Read only `score_result_snapshots` without submission status: rejected because lifecycle linkage becomes less inspectable.

## Decision 3: Compute trend deterministically using chronological windows

- **Decision**: Classify trend (`improving`, `stable`, `declining`) from deterministic comparison of recent-window mean accuracy vs prior-window mean accuracy.
- **Rationale**: Transparent, testable, and robust for short local histories.
- **Alternatives considered**:
  - LLM-derived trend labels: rejected by Principle I.
  - Linear regression-only approach: rejected as overkill for sparse household datasets.

## Decision 4: Send structured JSON context to the LLM

- **Decision**: Prompt receives a compact JSON payload (overall stats, per-skill metrics, trend label, notable weaknesses/strengths) and must return structured JSON with `summary_el` and `suggestions`.
- **Rationale**: Keeps prompt narrow, inspectable, and testable; enforces grounding in deterministic inputs.
- **Alternatives considered**:
  - Send raw SQL rows: rejected because it leaks persistence details and increases hallucination risk.
  - Free-form prose output only: rejected due to weak validation and parsing reliability.

## Decision 5: Graceful degradation when LLM is unavailable

- **Decision**: Always return deterministic report data. If LLM call fails or times out, set narrative status to degraded and provide a Greek fallback message without failing the command/page.
- **Rationale**: Required by `FR-007`, `SC-004`, and Principle VIII local-first resilience.
- **Alternatives considered**:
  - Hard-fail the command/page: rejected because parent still needs actionable deterministic metrics.
  - Retry loops with long backoff: rejected because it hurts responsiveness.

## Decision 6: Version prompt at `app/prompts/v1/progress_summary.md`

- **Decision**: Add a dedicated versioned prompt file and include prompt version metadata in report output.
- **Rationale**: Satisfies constitution prompt governance and `FR-010`.
- **Alternatives considered**:
  - Inline prompt in service code: rejected because prompt evolution would be hard to audit.
  - Reuse `explain_mistake.md`: rejected because role, schema, and constraints differ.

## Decision 7: Child filtering follows existing profile resolution semantics

- **Decision**: Reuse existing child lookup behavior (`_resolve_child`) for CLI and equivalent profile resolution for web query params.
- **Rationale**: Consistent UX across commands and avoids introducing conflicting identity rules.
- **Alternatives considered**:
  - Filter by free-text name directly in SQL: rejected because canonical key is `child_id`.
  - Hard-error on unknown child name: rejected in favor of friendly Greek no-data response.


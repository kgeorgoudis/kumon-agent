# Research - Manual Exercise Ingestion by Parent

## Decision 1: Use a CLI-guided confirmation workflow with two entry modes

- **Decision**: Implement `kumon submit <instance_id>` with both:
  - sequential prompt mode (default), and
  - bulk input mode (comma/space separated),
  followed by mandatory review + confirmation before persist/score.
- **Rationale**: Sequential mode minimizes mistakes for most parents; bulk mode optimizes speed for experienced users entering 10-20 answers.
- **Alternatives considered**:
  - **Bulk-only input**: faster but error-prone and poor correction UX.
  - **Sequential-only input**: safer but slower for repeated daily use.

## Decision 2: Normalize answers minimally, validate strictly, and preserve raw input

- **Decision**: Keep a raw entered value per answer and derive a normalized scoring value (`strip`, decimal comma normalization, simple numeric validation) during scoring.
- **Rationale**: Preserving raw input supports auditability while deterministic normalization avoids scoring drift from formatting differences.
- **Alternatives considered**:
  - **Aggressive auto-correction** (e.g., OCR-like substitutions): risks silently changing parent intent.
  - **No normalization at all**: creates false negatives for equivalent values like `3,5` vs `3.5`.

## Decision 3: Reject duplicate confirmed submissions, allow draft/resume

- **Decision**: Enforce one confirmed submission per `instance_id`; store interrupted/partial work as a draft that can be resumed or discarded.
- **Rationale**: Prevents accidental duplicate scoring while meeting the requirement to recover from interruptions.
- **Alternatives considered**:
  - **Allow unlimited confirmed submissions**: weakens audit clarity and progression stability.
  - **No drafts**: forces restart after interruption and degrades parent UX.

## Decision 4: Record optional timing as integer seconds

- **Decision**: Accept timing from CLI as `--time` (`SS`, `MM:SS`, or `12m` shorthand) and persist canonical integer seconds.
- **Rationale**: Seconds are deterministic, query-friendly, and easy to aggregate later for fluency metrics.
- **Alternatives considered**:
  - **Store original timing string only**: harder to compare and analyze.
  - **Require timing always**: conflicts with optional timing requirement.

## Decision 5: Trigger deterministic scoring immediately on confirmation

- **Decision**: On confirm, persist submission + answer entries, then run deterministic scoring using existing worksheet answer keys and persist score snapshot linked to submission.
- **Rationale**: Aligns with parent expectation of immediate feedback and preserves full lineage (`worksheet -> submission -> score`) in one flow.
- **Alternatives considered**:
  - **Deferred manual scoring command**: adds extra step and increases operational friction.
  - **LLM-assisted scoring**: violates deterministic-first constitutional constraints.

## Decision 6: Remove OCR/vision dependencies from ingestion path

- **Decision**: Manual submission path does not call image/OCR/vision code and does not require OCR fallback model availability.
- **Rationale**: Target device cannot reliably run dual-model OCR + vision fallback; manual entry is the robust local-first option.
- **Alternatives considered**:
  - **Keep OCR as default with manual fallback**: still fails on constrained hardware and adds complexity.
  - **Cloud OCR fallback**: conflicts with local-first and privacy defaults.


# Research: List Pending Worksheets

## Decision 1: Expose a dedicated CLI command `kumon pending`

- **Decision**: Add a top-level CLI command named `pending` (not replacing `history`).
- **Rationale**: The parent needs a fast recovery command after terminal restart. `history` currently lists all generated worksheets but does not answer "what can I still submit?".
- **Alternatives considered**:
  - Extend `kumon history` with status flags: rejected because it overloads the current command purpose and adds ambiguity.
  - Add only `--pending` to `history`: rejected because discoverability is weaker than a direct verb.

## Decision 2: Define "pending" as "no CONFIRMED manual submission"

- **Decision**: A worksheet is pending when there is no linked `manual_submissions` row with `status = confirmed`.
- **Rationale**: `confirm_and_score` is the deterministic completion boundary; drafts and cancellations are intentionally recoverable states and should remain actionable.
- **Alternatives considered**:
  - Exclude worksheets with draft submissions: rejected because parents explicitly need to continue incomplete work.
  - Treat any submission row as complete: rejected because it conflicts with current draft/cancel lifecycle semantics.

## Decision 3: Use a database query in persistence layer (NOT EXISTS confirmed)

- **Decision**: Add persistence method(s) to fetch pending worksheet instances, backed by SQL that excludes confirmed submissions via `NOT EXISTS`.
- **Rationale**: Keeps business rule centralized and reusable by CLI/Web, aligns with shared service logic principle, and avoids expensive in-memory filtering.
- **Alternatives considered**:
  - Fetch all worksheets and filter in CLI: rejected due to duplicated logic and poor scaling.
  - Filter in submission service only: rejected because persistence is the appropriate place for relational filtering.

## Decision 4: Include draft indicator in response projection

- **Decision**: Return a lightweight projection that includes whether a draft exists for each pending worksheet.
- **Rationale**: Edge cases in the spec require visibility into draft state without changing pending eligibility.
- **Alternatives considered**:
  - No indicator: rejected because parent cannot distinguish fresh vs resumable items.
  - Compute draft indicator in CLI with per-row DB calls: rejected due to N+1 query risk.

## Decision 5: Keep child filtering behavior consistent with existing CLI

- **Decision**: Reuse `_resolve_child` semantics in CLI; if child filter resolves to a profile, query by `child_id`; if no profile exists, show no pending rows with a friendly Greek message.
- **Rationale**: Preserves current UX patterns and avoids introducing a second identity resolution rule.
- **Alternatives considered**:
  - Filter by display-name text join in SQL: rejected because worksheet stores `child_id`, not display name.
  - Hard-fail on unknown child name: rejected because current CLI favors soft handling with friendly output.

## Decision 6: Table output must show full copyable instance ID

- **Decision**: In `kumon pending` output, display full `instance_id` string (no truncation), plus core context columns (date, title, exercises, submission state hint).
- **Rationale**: FR-006 requires direct copy-paste into `kumon submit <id>`.
- **Alternatives considered**:
  - Truncated IDs with hover/detail: rejected for terminal workflow.
  - Separate `--full-id` flag: rejected because full ID is the primary task, not an advanced option.


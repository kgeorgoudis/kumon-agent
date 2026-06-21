# Research: Ordering Numbers Skill

## Decision 1: Extend the existing `Exercise` model rather than creating a separate ordering-only entity

- **Decision**: Add optional metadata fields to `Exercise` for ordering-specific content (e.g. source number list, direction, canonical answer string) while preserving the current model for arithmetic worksheets.
- **Rationale**: `WorksheetInstance`, persistence, templates, CLI review, and scoring already depend on a single `Exercise` list. Extending the shared model keeps CLI/web/service reuse intact and avoids a split worksheet pipeline.
- **Alternatives considered**:
  - Create a second `OrderingExercise` type: rejected because `WorksheetInstance.exercises` persistence, rendering, and submission flows currently assume one homogeneous model.
  - Encode everything only in `problem_text`: rejected because scoring and future OCR review need inspectable structured fields, not fragile display-string parsing.

## Decision 2: Represent the correct ordering answer as a canonical space-joined sequence string

- **Decision**: Store the correct ordered result in a deterministic canonical text form such as `"3 12 45 108"`, while also preserving the structured source list and direction metadata.
- **Rationale**: Current manual scoring infrastructure compares normalized strings and stores them in `manual_answer_entries.normalized_value` and score snapshot details. A canonical plain-text sequence fits that pipeline with minimal schema disruption.
- **Alternatives considered**:
  - Store only a Python list in `answer`: rejected because current `submission_service` and score snapshot payloads already serialize expected answers as strings.
  - Use comma-separated canonical answers: rejected because bulk CLI submission already uses commas between exercises, causing ambiguous parsing.

## Decision 3: Use explicit ordering directions with per-exercise Greek prompts embedded in `problem_text`

- **Decision**: Each generated exercise will include its own direction in Greek within `problem_text`, e.g. `"Αύξουσα: 17, 5, 42, 30 → ___"` or `"Φθίνουσα: 120, 9, 45, 78 → ___"`.
- **Rationale**: This keeps each exercise self-contained on paper, avoids ambiguity when a worksheet mixes ascending and descending tasks, and works with the existing generic worksheet template that renders `problem_text` directly.
- **Alternatives considered**:
  - One worksheet-level instruction only: rejected because mixed directions become ambiguous.
  - Add direction-only icons/arrows with no Greek word: rejected because text clarity is more important than compactness for a child-facing worksheet.

## Decision 4: Normalize submitted ordering answers by extracting integers and canonicalizing separators

- **Decision**: For `ordering_numbers`, normalize parent-entered answers by extracting integer tokens from the raw text, preserving order, and re-joining them with single spaces for comparison.
- **Rationale**: This tolerates common formatting variation (`1 4 9`, `1,4,9`, `1 - 4 - 9`) while keeping whole-sequence scoring deterministic and inspectable.
- **Alternatives considered**:
  - Strict raw-string equality: rejected because harmless spacing/punctuation differences would create false negatives.
  - Numeric sorting during scoring: rejected because it would incorrectly mark unordered input as correct by repairing parent-entered mistakes.

## Decision 5: Reserve semicolon-delimited bulk submission for sequence-answer worksheets

- **Decision**: For CLI bulk submission, document and support semicolon (`;`) as the delimiter between exercises when a worksheet uses sequence-style answers, while commas/spaces inside one answer remain valid.
- **Rationale**: The current parser uses commas to separate exercises, which conflicts with natural sequence formatting for ordering answers. A top-level semicolon delimiter preserves copy-paste usability without breaking scalar worksheet behavior.
- **Alternatives considered**:
  - Require space-only within each sequence and keep commas between exercises: rejected because it is easy for parents to type commas naturally inside a sequence.
  - Add a separate submit command for ordering worksheets: rejected because it would violate the shared workflow principle and increase UX complexity.

## Decision 6: Generate 4-6 distinct numbers with balanced ascending/descending direction and age-appropriate range mix

- **Decision**: Each exercise will sample 4-6 distinct numbers drawn from a deterministic mix of 1-digit, 2-digit, and 3-digit values up to 1000, and alternate or randomly balance ascending vs descending directions using the same RNG seed.
- **Rationale**: This matches the spec’s difficulty target, avoids degenerate duplicate-number cases, and keeps worksheets varied but reproducible.
- **Alternatives considered**:
  - Fixed-length 4-number exercises only: rejected because a little variation better matches incremental Kumon-style fluency practice.
  - Pure 3-digit range only: rejected because level 2 should still include easier items and mixed visual comparison practice.

## Decision 7: Keep templates generic and drive ordering presentation entirely through `problem_text` / `answer_text`

- **Decision**: Reuse the existing worksheet and answer-key templates, only validating that longer sequence strings remain legible; update CSS/template only if readability requires it.
- **Rationale**: The templates already render arbitrary `problem_text` and `answer_text` values. Reusing them keeps implementation small and aligned with the repo’s preference for boring correctness.
- **Alternatives considered**:
  - Add a custom ordering worksheet template: rejected because it duplicates layout logic for one micro-skill.
  - Render ordering answers as separate HTML list elements: rejected because existing generic text rendering is sufficient for v1.


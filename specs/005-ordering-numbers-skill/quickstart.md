# Quickstart: Ordering Numbers Skill

## Prerequisites

- Local project dependencies installed via `uv`.
- Existing workspace write access for `output/worksheets/`.
- Optional: an existing child profile if you want to generate for a named child.

## Happy Path

1. Generate an ordering worksheet:
   - `uv run kumon generate ordering-numbers --exercises 6 --seed 42 --no-open`
2. Confirm output shows `Διάταξη Αριθμών` and the worksheet/answer-key paths.
3. Open the generated worksheet HTML and verify each exercise includes:
   - Greek direction text (`Αύξουσα` or `Φθίνουσα`)
   - 4-6 numbers
   - printable blank answer area
4. Submit correct answers in bulk using semicolons between exercises:
   - `uv run kumon submit <instance_id> --answers "...; ...; ..." --no-confirm`
5. Confirm deterministic scoring returns the expected accuracy.

## Determinism Check

1. Generate twice with the same seed:
   - `uv run kumon generate ordering-numbers --exercises 5 --seed 99 --no-open`
   - `uv run kumon generate ordering-numbers --exercises 5 --seed 99 --no-open`
2. Verify the exercise texts match exactly.

## Manual Review / Input Tolerance Check

1. Generate one ordering worksheet.
2. Submit answers using mixed internal separators such as commas or dashes within one answer.
3. Confirm normalization still scores correctly if the order is correct.
4. Confirm an incorrectly ordered sequence is marked wrong even if it contains the same numbers.

## Suggested Test Command

Run the focused regression suite after implementation:

- `uv run pytest -q app/tests/test_math_engine.py app/tests/test_worksheet_generator.py app/tests/test_submission_service.py app/tests/test_cli_submit.py app/tests/test_progression_service.py app/tests/test_database.py`

## Validation Checklist

- `kumon generate ordering-numbers` no longer raises `ValueError`.
- Same seed yields identical ordering exercises.
- All generated ordering exercises contain distinct numbers only.
- Answer key displays the correctly ordered sequence.
- Manual scoring treats the whole sequence as the unit of correctness.
- Semicolon-delimited bulk submit works for ordering worksheets.
- Progression decision is persisted after confirmed ordering submissions.
- Existing arithmetic worksheet generation and submission tests still pass.

## Validation Notes

- Focused run (2026-06-19):
  - `uv run pytest -q app/tests/test_math_engine.py app/tests/test_worksheet_generator.py app/tests/test_submission_service.py app/tests/test_cli_submit.py app/tests/test_progression_service.py app/tests/test_database.py`
  - Result: `92 passed`


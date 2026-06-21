# CLI Contract: Ordering Numbers Skill

## Commands in Scope

### `kumon generate ordering-numbers`

Generate a printable worksheet for the `ordering_numbers` micro-skill using the existing worksheet pipeline.

#### Syntax

```bash
kumon generate ordering-numbers [--exercises <n>] [--seed <seed>] [--child <name>] [--no-open]
```

#### Output Semantics

- Success prints the standard worksheet summary panel with:
  - Greek skill title `Διάταξη Αριθμών`
  - worksheet instance ID
  - worksheet HTML path
  - answer key HTML path
- Generated worksheet contains one exercise per slot with:
  - a clear Greek direction (`Αύξουσα` or `Φθίνουσα`)
  - a list of 4-6 numbers
  - a blank answer area

#### Determinism Guarantee

- Re-running the same command with the same `--seed` and `--exercises` value produces the same exercises and answer key.

## Submission Contract Impact

### `kumon submit <instance_id>` for ordering worksheets

The existing submit command remains the entry point for manually entered ordering answers.

#### Accepted Answer Formats Per Exercise

For one ordering exercise, the parent may enter the ordered sequence using flexible separators inside the answer, for example:

- `5 17 42 108`
- `5, 17, 42, 108`
- `5 - 17 - 42 - 108`

The system normalizes these to a canonical space-joined sequence.

#### Bulk Submission Rule for Ordering Worksheets

When submitting all answers at once for an ordering worksheet, exercises MUST be separated with semicolons.

```bash
kumon submit <instance_id> --answers "1 3 5 8; 44, 31, 20, 9; 7 12 18 100" --no-confirm
```

This prevents ambiguity with commas used inside a single sequence answer.

#### Success Output

- The command continues to print the standard score summary:
  - confirmed submission ID
  - correct count / total count
  - accuracy percentage
  - optional duration

#### Failure Cases

- `ERR_WORKSHEET_NOT_FOUND`
  - Trigger: worksheet ID does not exist.
- `ERR_ANSWER_COUNT_MISMATCH`
  - Trigger: number of provided bulk answers does not match exercise count.
- `ERR_INVALID_ANSWER_FORMAT`
  - Trigger: one or more ordering answers cannot be normalized into a valid numeric sequence.
- `ERR_SUBMISSION_ALREADY_CONFIRMED`
  - Trigger: a confirmed submission already exists for the worksheet.

## Compatibility Notes

- Scalar-answer worksheets keep their current submit behavior.
- `kumon list-skills` and `kumon generate ordering-numbers` must now agree: if the skill is listed, worksheet generation succeeds.


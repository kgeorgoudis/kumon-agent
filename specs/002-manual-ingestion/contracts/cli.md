# CLI Contract - Manual Exercise Ingestion

## Command: `kumon submit`

Submit manually transcribed answers for a generated worksheet and trigger deterministic scoring.

## Syntax

```bash
kumon submit <instance_id> [--answers "a1,a2,..."] [--time <duration>] [--resume] [--no-confirm]
```

## Arguments

- `instance_id` (required): worksheet instance identifier.

## Options

- `--answers` (optional): bulk answers as comma-separated or whitespace-separated values.
- `--time` (optional): completion duration (`SS`, `MM:SS`, or `12m`).
- `--resume` (optional, flag): resume latest draft submission for the same `instance_id` if available.
- `--no-confirm` (optional, flag): skip interactive confirmation prompt (only valid when `--answers` is provided and complete).

## Interactive Flow (default)

1. Validate `instance_id` exists.
2. Reject immediately if a confirmed submission already exists for that worksheet.
3. Prompt sequentially for each exercise slot (unless `--answers` provided).
4. Show review table with all entered answers.
5. Allow targeted correction by slot number.
6. Confirm submission.
7. Persist submission + answer entries.
8. Run deterministic scoring.
9. Print Greek-friendly result summary.

## Success Output (example)

```text
✅ Η υποβολή αποθηκεύτηκε
Worksheet ID: 4ab1...
Submission ID: 812e...
Ακρίβεια: 86.67%
Σωστές απαντήσεις: 13/15
Χρόνος: 12:34
```

## Error Contract

- `ERR_WORKSHEET_NOT_FOUND`
  - Trigger: `instance_id` does not map to an existing worksheet.
  - Exit code: `1`

- `ERR_SUBMISSION_ALREADY_CONFIRMED`
  - Trigger: a confirmed submission exists for the worksheet instance.
  - Exit code: `1`

- `ERR_ANSWER_COUNT_MISMATCH`
  - Trigger: provided bulk answers count does not equal exercise count.
  - Exit code: `1`

- `ERR_INVALID_ANSWER_FORMAT`
  - Trigger: one or more answers cannot be normalized/validated.
  - Exit code: `1`

- `ERR_DRAFT_NOT_FOUND`
  - Trigger: `--resume` requested but no draft exists.
  - Exit code: `1`

- `ERR_SUBMIT_CANCELLED`
  - Trigger: user aborts confirmation or exits during entry.
  - Exit code: `130` for Ctrl+C, otherwise `1`.

## Determinism Guarantees

- Scoring input is based on persisted normalized answers ordered by `slot_index`.
- Input hashing ensures identical confirmed input produces identical score snapshots.
- No OCR/vision/remote model call occurs in this command.


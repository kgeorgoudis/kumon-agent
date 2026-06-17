# Quickstart - Manual Exercise Ingestion by Parent

## Prerequisites

- Python 3.12+
- `uv` installed
- Existing generated worksheet instance in local DB

## Install

```bash
uv sync --dev
```

## Generate a worksheet (if needed)

```bash
uv run kumon generate multiplication-2-5 --exercises 15 --no-open
```

Copy the `ID` from the output — you'll use it as `<instance_id>`.

## Submit answers manually (interactive)

```bash
uv run kumon submit <instance_id>
```

The system prompts for each answer one at a time showing the exercise (e.g. `7 × 8 = ___`).
After all answers are entered a review table is shown — type `y` to confirm or `n` to correct a slot.

## Submit answers manually (bulk)

```bash
uv run kumon submit <instance_id> --answers "2,4,6,8,10,12,14,16,18,20,22,24,26,28,30"
```

The `--no-confirm` flag skips the interactive confirmation step (useful for scripting):

```bash
uv run kumon submit <instance_id> --answers "2,4,6,8,10,12,14,16" --no-confirm
```

## Submit with optional timing

```bash
uv run kumon submit <instance_id> --time 12:34
uv run kumon submit <instance_id> --time 9m
uv run kumon submit <instance_id> --time 120
```

Formats: `SS` (seconds), `MM:SS`, or `Xm` (minutes).

## Resume an interrupted draft

```bash
uv run kumon submit <instance_id> --resume
```

## Validation scenarios

```bash
# Unknown worksheet → ERR_WORKSHEET_NOT_FOUND (exit 1)
uv run kumon submit does-not-exist

# Wrong number of bulk answers → ERR_ANSWER_COUNT_MISMATCH (exit 1)
uv run kumon submit <instance_id> --answers "1,2,3"

# Duplicate confirmed submission → ERR_SUBMISSION_ALREADY_CONFIRMED (exit 1)
uv run kumon submit <instance_id> --answers "..." --no-confirm  # first time OK
uv run kumon submit <instance_id> --answers "..." --no-confirm  # second time fails

# Invalid timing → ERR_INVALID_DURATION_FORMAT (exit 1)
uv run kumon submit <instance_id> --answers "..." --time "99:99"
```

## Run tests

```bash
uv run pytest -v app/tests/test_submission_service.py app/tests/test_cli_submit.py
```

To run the full suite including regression:

```bash
uv run pytest -v
```

## Expected outcomes

- Parent enters 10-20 answers without OCR/image tooling.
- Confirmation review allows targeted slot correction before scoring.
- On confirm, deterministic scoring runs automatically and prints Greek-friendly results.
- Audit lineage is traceable: worksheet → manual submission → score snapshot.
- Fully local operation; no OCR, vision model, or network required.
- Incorrect answer format is rejected early with a clear error code.

## Quickstart Validation (2026-06-17)

✅ **All commands tested and working**:
- `kumon submit <id>` interactive mode → prompts per slot, review table, score displayed
- `kumon submit <id> --answers "..." --no-confirm` → bulk mode, instant score
- `kumon submit <id> --time 9m` → timing stored and displayed as `9:00`
- `kumon submit <id> --resume` with no draft → `ERR_DRAFT_NOT_FOUND`
- Duplicate confirmed submission → `ERR_SUBMISSION_ALREADY_CONFIRMED`

Full test suite: **110/110 pass**, **0 network dependencies**, **~2 seconds** total.

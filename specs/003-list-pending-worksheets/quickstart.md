# Quickstart: List Pending Worksheets

## Prerequisites

- Existing local database (`data/kumon.db`) or a test database.
- At least one generated worksheet (`kumon generate ...`).

## Happy Path

1. Generate worksheets:
   - `kumon generate multiplication-2-5 --exercises 10`
   - `kumon generate addition-single-digit --exercises 8`
2. Submit one worksheet:
   - `kumon submit <worksheet_id> --answers "..." --no-confirm`
3. List pending worksheets:
   - `kumon pending`
4. Copy one `Worksheet ID` from output and submit:
   - `kumon submit <worksheet_id_from_pending>`

## Child Filter

- Show pending only for one child:
  - `kumon pending --child "Ελένη"`

## Validation Checklist

- Confirmed worksheet IDs do not appear in `kumon pending`.
- Draft/cancelled worksheet IDs still appear.
- IDs in table are full UUID values and copy-paste into `kumon submit` works.
- Ordering is newest-first.

## Suggested Test Command

Run focused tests after implementation:

- `uv run pytest -q app/tests/test_database.py app/tests/test_cli_pending.py app/tests/test_cli_submit.py app/tests/test_submission_service.py`

## Validation Notes

- 2026-06-17: Focused regression suite passed (`48 passed`).

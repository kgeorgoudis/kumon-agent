# CLI Contract: Pending Worksheets

## Command

`kumon pending`

## Purpose

List worksheets that can still be submitted (i.e., no confirmed manual submission exists yet), so the parent can copy a worksheet ID for `kumon submit`.

## Options

- `--child`, `-c` (optional, string): filter to one child profile name.
- `--limit`, `-n` (optional, int, default: 20): maximum rows returned.

## Input Semantics

- If `--child` is provided:
  - CLI resolves the profile via existing `_resolve_child` flow.
  - If profile resolves, use `child_id` filter.
  - If profile does not resolve, command returns zero rows and a friendly Greek message.

## Output Semantics

### Success with rows

Render a Rich table with columns:

1. `Ημερομηνία` (formatted `YYYY-MM-DD HH:MM`)
2. `Δεξιότητα`
3. `Ασκήσεις`
4. `Πρόχειρο` ("Ναι" if draft exists, else "—")
5. `Worksheet ID` (full instance_id, untruncated)

Rows sorted by `created_at DESC`.

### Success with no rows

Print Greek-friendly informational message:

- Unfiltered: `Δεν υπάρχουν εκκρεμή φύλλα για υποβολή.`
- With child filter: `Δεν υπάρχουν εκκρεμή φύλλα για υποβολή για το παιδί '<name>'.`

### Failure cases

- No fatal error expected for "unknown child" (handled as empty result).
- Unexpected DB/service errors return non-zero exit code with existing CLI error style.

## Compatibility Notes

- Does not change `kumon history` behavior.
- Returned IDs are directly compatible with existing `kumon submit <instance_id>` command.


# CLI Contract: Progress Summary

## Command

`kumon progress`

## Purpose

Generate a parent-friendly Greek progress report for one child using deterministic worksheet history, with optional LLM narrative summary and next-step suggestions.

## Options

- `--child`, `-c` (optional, string): child display name.
- `--limit`, `-n` (optional, int, default: 20): max confirmed worksheets included (most recent first before trend ordering).
- `--no-llm` (optional, flag): skip LLM narrative and show deterministic report only.

## Input Semantics

- If `--child` is provided, resolve to `child_id` using existing profile resolution behavior.
- If child cannot be resolved, return friendly Greek no-data/error message (non-fatal).
- If no child is provided, use default profile behavior consistent with existing CLI commands.

## Output Semantics

### Success with report data

Render sections in Greek:

1. Report header (child, worksheet count, date range)
2. Deterministic metrics (overall accuracy, trend)
3. Per-skill table (`micro_skill`, count, avg accuracy, trend)
4. Narrative summary section (if LLM generated or fallback)
5. Suggestions list (grounded actionable next steps)

### Success with no scored worksheets

Print: `Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα για αναφορά προόδου.`

### LLM degraded mode

- Command still exits `0`.
- Deterministic sections always printed.
- Include warning line such as `Η αφήγηση LLM δεν ήταν διαθέσιμη. Εμφανίζονται μόνο ντετερμινιστικά δεδομένα.`

### Failure cases

- Unexpected DB/service errors return non-zero exit code and existing CLI error style.

## Compatibility Notes

- Does not alter scoring, progression, or worksheet generation behavior.
- Suggestions are advisory only; no automatic progression writeback.


# Quickstart: Progress Summary

## Prerequisites

- Local database exists (`data/kumon.db`).
- At least one child profile exists.
- At least two confirmed submissions with score snapshots for meaningful trends.
- Optional: local LLM endpoint is running for narrative generation.

## Happy Path (CLI)

1. Generate and submit a few worksheets for the same child.
2. Run progress summary:
   - `kumon progress --child "Ελένη"`
3. Validate output includes:
   - Date range
   - Overall accuracy + trend
   - Per-skill breakdown
   - Suggestions in Greek

## Deterministic Fallback Path

1. Stop or disconnect local LLM endpoint.
2. Run:
   - `kumon progress --child "Ελένη"`
3. Confirm command still shows deterministic metrics and a degraded-mode warning.

## Web Path

1. Start web app (project-specific run command).
2. Open:
   - `/progress?child=Ελένη`
3. Confirm the same metrics and suggestions appear as in CLI output.

## Suggested Test Command

Run focused regression tests after implementation:

- `uv run pytest -q app/tests/test_progress_summary_service.py app/tests/test_cli_progress.py app/tests/test_web_progress.py`

Focused implementation run (2026-06-18):

- `uv run pytest -q app/tests/test_progress_summary_service.py app/tests/test_cli_progress.py app/tests/test_web_progress.py app/tests/test_database.py`

Result: `30 passed`

Full suite validation (2026-06-18):

- `uv run pytest -q`

Result: `124 passed`

## Validation Checklist

- Summary never uses LLM as score source of truth.
- Suggested skills are grounded in historical practiced skills.
- No-data and degraded modes are user-friendly in Greek.
- CLI and web outputs come from the same service payload.


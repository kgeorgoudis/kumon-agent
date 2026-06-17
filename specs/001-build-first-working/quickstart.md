# Quickstart - First Working Version (V1)

## Prerequisites
- Python 3.12+
- `uv` installed

## Install
```bash
uv sync --dev
```

## Run core flow
```bash
uv run kumon list-skills
uv run kumon profile create "Ελένη" --age 10 --grade 4
uv run kumon generate multiplication-2-5 --child "Ελένη" --exercises 15 --no-open
uv run kumon history --child "Ελένη"
```

## Validate in-app docs
```bash
uv run kumon explain method
uv run kumon explain skill multiplication
uv run kumon explain progression
```

## Run tests
```bash
uv run pytest -v
```

## Expected outputs

### Worksheet Generation
- Two HTML files created in `output/worksheets/<YYYY-MM-DD>/`:
  - `{instance_id}_worksheet.html` — child-facing, A4 printable, Greek instructions
  - `{instance_id}_answer_key.html` — parent-facing with answers highlighted
- Both files are deterministic (same seed → same exercises)
- Exercises are Python-generated, never LLM-derived

### In-App Documentation
- `kumon explain method` shows a practical Kumon guides in English
- `kumon explain skill <name>` shows skill details with micro-skills and Greek descriptions
- `kumon list-skills --verbose` shows difficulty levels and Greek text
- All documentation is locally embedded (no internet required)

### Local Persistence
- SQLite DB created at `data/kumon.db` after first profile/worksheet
- Worksheets persist with full metadata
- History retrieval works across CLI sessions
- Profile settings apply to subsequent generations

### Test Summary
- 39/39 tests pass offline in ~0.2 seconds
- Coverage includes:
  - ✅ Deterministic exercise generation
  - ✅ HTML rendering with Greek content
  - ✅ SQLite persistence and queries
  - ✅ CLI command routing
  - ✅ Seed reproducibility

## Quickstart Validation (v0.1.0)

✅ **All commands tested and working** (2026-06-14):
- `kumon list-skills` → displays 14 skills with Greek names and difficulty
- `kumon profile create "Γιάννης"` → saves profile to database
- `kumon generate subtraction-with-borrowing --child "Γιάννης"` → worksheet + answer key created
- `kumon history --child "Γιάννης"` → historical worksheets retrieved
- `kumon explain method` → in-app method guidance available
- Full test suite: **39/39 pass**, **0 network dependencies**

**Ready for parent pilot testing** — core v1 loop is functional and stable.

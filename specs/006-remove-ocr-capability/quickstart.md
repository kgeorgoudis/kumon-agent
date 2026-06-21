# Quickstart: Validate Manual-Only Workflow

## 1) Run test suite

```zsh
cd /Users/K.Georgoudis/code/labs/kumon-agent
uv run pytest app/tests/
```

Expected: all tests pass and no OCR test modules exist.

## 2) Generate worksheet

```zsh
cd /Users/K.Georgoudis/code/labs/kumon-agent
uv run kumon generate addition-single-digit --exercises 5 --no-open
```

Copy the printed worksheet `instance_id` from command output.

## 3) Submit answers manually

```zsh
cd /Users/K.Georgoudis/code/labs/kumon-agent
uv run kumon submit <instance_id> --answers "1,2,3,4,5" --no-confirm
```

Expected:
- submission is confirmed,
- deterministic score is printed,
- score snapshot is persisted.

## 4) Check pending/progress commands still work

```zsh
cd /Users/K.Georgoudis/code/labs/kumon-agent
uv run kumon pending
uv run kumon progress
```

Expected: no OCR-related output or errors.

## 5) Verify dependency cleanup

```zsh
cd /Users/K.Georgoudis/code/labs/kumon-agent
grep -n "pytesseract\|pypdfium2\|pillow\|python-magic" pyproject.toml
```

Expected: no matches.


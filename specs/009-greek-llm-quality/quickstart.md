# Quickstart: Improve Greek LLM Response Quality

**Feature**: 009-greek-llm-quality  
**Branch**: `009-greek-llm-quality`

---

## What changes

| Area | Change |
|------|--------|
| `app/prompts/v2/` | New prompt directory with tighter persona + few-shot example for progress |
| `app/config.py` | New `PROMPT_VERSION` config var (default `"v2"`, override via `KUMON_PROMPT_VERSION`) |
| `app/agents/prompt_registry.py` | Reads `PROMPT_VERSION` to resolve the prompts directory |
| `app/agents/agent_graph.py` | Hardened JSON extraction (think-block stripping, regex object search); one retry on bad output; two new validation checks |
| `app/tests/test_greek_quality.py` | New test file: heuristic quality checks on v2 prompt artefacts |

---

## Running the feature locally

### Prerequisites

- `uv` installed and project dependencies installed (`uv sync`)
- Local LLM server running at `http://127.0.0.1:8000/v1` with
  `Qwen3-4B-MLX-4bit` (or any OpenAI-compatible model)
- At least one child profile with graded worksheets in the database

### 1. Verify model name in `.env`

```bash
# .env (project root)
KUMON_LLM_MODEL=Qwen3-4B-MLX-4bit
# KUMON_PROMPT_VERSION=v2  ← this is the default; only set if you want v1
```

### 2. Run the progress command

```bash
uv run kumon progress -c <child_id>
```

Expected: Greek `summary_el` text with no grammar errors, grounded in the
child's actual worksheet data.

### 3. Rollback to v1 prompts

```bash
KUMON_PROMPT_VERSION=v1 uv run kumon progress -c <child_id>
```

### 4. Run the test suite

```bash
uv run pytest app/tests/ -v
```

All existing tests must continue to pass. New tests in
`test_greek_quality.py` must pass.

### 5. Inspect traces on degraded runs

If the narrative degrades, the error code is visible in the CLI output and
stored in the database:

```bash
uv run kumon traces list --status DEGRADED --type PROGRESS_REPORT
uv run kumon traces show <task_id>
```

New error codes to look for:
- `ERR_LLM_EMPTY_SUMMARY` — model returned blank summary
- `ERR_LLM_WRONG_LANGUAGE` — model responded in English

---

## Key files

```text
app/prompts/v2/kumon_tutor_persona.md   ← tighter persona
app/prompts/v2/progress_summary.md      ← few-shot example + tighter task
app/agents/agent_graph.py               ← robust extraction + retry + new error codes
app/agents/prompt_registry.py           ← version-aware prompt loader
app/config.py                           ← PROMPT_VERSION
app/tests/test_greek_quality.py         ← new quality heuristic tests
```

---

## Verification checklist

- [ ] `uv run kumon progress -c <child_id>` produces grammatically correct Greek `summary_el`
- [ ] No `ERR_LLM_INVALID_JSON` in traces for normal runs
- [ ] Setting `KUMON_PROMPT_VERSION=v1` reverts to previous behaviour
- [ ] All pytest tests pass: `uv run pytest app/tests/ -v`
- [ ] New `test_greek_quality.py` tests pass
- [ ] Degraded runs still show correct error codes in `kumon traces show <id>`


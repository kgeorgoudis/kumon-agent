# Implementation Plan: Improve Greek LLM Response Quality

**Branch**: `009-greek-llm-quality` | **Date**: 2026-06-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-greek-llm-quality/spec.md`

## Summary

Improve Greek narrative quality and reliability for the `kumon progress` command
when using the small Qwen3-4B-MLX-4bit model. The strategy is three-pronged:
(1) rewrite the progress prompt as `v2` with tighter constraints and concrete
few-shot examples that teach the model the exact output shape; (2) harden the
JSON extraction in the agent graph to tolerate Qwen3 think-block leakage and
embedded JSON; (3) extend the validation gate with additional quality checks.
No new entities or external dependencies are introduced.

## Technical Context

**Language/Version**: Python 3.12, managed with `uv`

**Primary Dependencies**: LangGraph ≥ 0.2, `openai` ≥ 1.50 (OpenAI-compatible
client for local model), Pydantic ≥ 2.9, pytest ≥ 8.3

**Storage**: SQLite via `app/persistence/database.py` — no schema changes needed

**Testing**: pytest. Fixture-based unit tests for prompt loading, JSON
extraction, and validation node; parametric tests for Greek output quality
heuristics.

**Target Platform**: macOS, local inference at `http://127.0.0.1:8000/v1`

**Project Type**: CLI + FastAPI web service (single `app/` package)

**LLM Model**: Qwen3-4B-MLX-4bit (user's `.env` override via
`KUMON_LLM_MODEL`; constitution documents `Qwen3-8B-MLX-4bit` as default)

**Performance Goals**: Progress command should still return within the current
LLM timeout (30 s default). At most one automatic retry per run.

**Constraints**: No new Python package dependencies. Changes must be
backward-compatible with v1 prompts so a single env-var switch can revert.

**Scale/Scope**: Single operator, single child session. Low concurrency.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| **I — Deterministic Before Agentic** | Feature touches only the LLM-narrative path; all scoring and progression remain deterministic | ✅ PASS |
| **II — Arithmetic Truth From Code** | No arithmetic computation moved to or from the LLM | ✅ PASS |
| **VII — Greek-First Content** | The entire feature exists to improve Greek quality; child/parent output stays Greek | ✅ PASS |
| **VIII — Local-First Architecture** | No external LLM calls added; model stays at `http://127.0.0.1:8000/v1` | ✅ PASS |
| **IX — Shared Domain Logic** | Prompt and extraction changes live in `app/agents/` and `app/prompts/`, shared by CLI and web | ✅ PASS |
| **XI — Kumon Tutor Persona** | Persona is refined and strengthened with examples; not weakened or removed | ✅ PASS |
| **XII — Agent Observability** | No changes to trace persistence; new error code `ERR_LLM_EMPTY_SUMMARY` adds observability | ✅ PASS |
| **Prompt Versioning** | New prompts land in `app/prompts/v2/`; registry gains a version-config path; v1 stays intact | ✅ PASS |

**Post-design re-check**: See bottom of Phase 1.

## Project Structure

### Documentation (this feature)

```text
specs/009-greek-llm-quality/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── progress_narrative_v2.md
└── tasks.md             ← Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
app/
├── agents/
│   ├── agent_graph.py          ← improve _extract_json_block; add retry; new error code
│   └── prompt_registry.py      ← support prompt version config
├── config.py                   ← add PROMPT_VERSION env var (default "v2")
└── prompts/
    ├── v1/                      ← UNCHANGED (kept for rollback)
    └── v2/
        ├── kumon_tutor_persona.md   ← tighter persona, explicit Greek-only rule
        └── progress_summary.md     ← tighter task + 1 few-shot example

app/tests/
├── test_agent_graph.py          ← extend: new extraction cases, retry, new error code
├── test_prompt_registry.py      ← extend: v2 loading and version-switch test
└── test_greek_quality.py        ← NEW: heuristic quality checks on v2 prompt output
```

**Structure Decision**: Single-project layout. All changes are within the
existing `app/` package. No new top-level directories.

## Complexity Tracking

No constitution violations. No complexity justification required.

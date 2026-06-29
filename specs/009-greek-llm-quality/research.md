# Research: Improve Greek LLM Response Quality

**Feature**: 009-greek-llm-quality  
**Date**: 2026-06-29  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## R-001: Few-shot prompting for small quantized Greek-language models

**Decision**: Add exactly one concrete input/output example directly in the
`progress_summary.md` task prompt (the USER turn, before the real payload).

**Rationale**: Models with ≤7B parameters (including 4-bit quantized variants)
rely heavily on demonstration rather than instruction alone. A single well-formed
example reduces the model's search space for both structure (what JSON to emit)
and register (simple, qualitative Greek sentences). Two or more examples
increase prompt token count without meaningfully improving output at this scale.
Placement in the USER turn — not the SYSTEM turn — keeps the system block short
and separates the demonstration from the constraint set.

**Alternatives considered**:
- Relying on instruction-only prompting (current v1 approach): produces
  structural variety and occasional English fragments in 4B models.
- Chain-of-thought with scratchpad: increases output length and consumes
  token budget that must be reserved for JSON; incompatible with `/no_think`
  mode already in use.
- Multiple examples (3-shot): prompt becomes longer than the model's effective
  context attention window for instructions; diminishing returns past 1-2 shots.

---

## R-002: Qwen3 think-block leakage in JSON extraction

**Decision**: Replace the current positional `_extract_json_block` approach with
a two-step extraction:
1. Strip any `<think>…</think>` block from the beginning of the raw response.
2. Use `re.search(r'\{[\s\S]*?\}', text, re.DOTALL)` with a greedy outer match
   to locate the first complete JSON object regardless of surrounding prose.

**Rationale**: Qwen3 models emit `<think>…</think>` tokens even when
`/no_think` is appended to the user message, particularly when the model is
small (4B) or when the server does not honour the directive. The current
`_extract_json_block` only strips leading triple-backtick fences, so any think
block silently causes `ERR_LLM_INVALID_JSON`. A greedy regex for the outermost
`{…}` correctly handles:
- Raw JSON with no fencing
- JSON wrapped in ` ```json … ``` `
- JSON preceded by `<think>…</think>`
- JSON followed by trailing prose

**Alternatives considered**:
- Parsing every line until valid JSON is found: fragile against multi-line JSON.
- Requiring the server to strip think tokens: not portable; cannot be
  controlled from the client side for all mlx-lm server versions.
- Extending `LLM_THINKING_ENABLED` flag to strip client-side: correct
  direction, implemented here as part of the extraction step.

---

## R-003: Output validation — catching hallucinations and empty strings

**Decision**: Extend the existing `_validation_node` with three additional
checks for the `PROGRESS_REPORT` task type:

1. **Empty-summary guard**: if `summary_el` is an empty string or whitespace
   only, set `ERR_LLM_EMPTY_SUMMARY` and degrade.
2. **English-leak guard**: if `summary_el` contains a run of ≥ 5 consecutive
   ASCII word characters matching common English stop-words (`the`, `is`, `and`,
   `for`, `of`, `that`) → set `ERR_LLM_WRONG_LANGUAGE` and degrade. This is a
   lightweight heuristic, not a full language-detector, so it avoids a new
   dependency.
3. **Skill-hallucination guard** (already partially present via
   `_normalize_suggestions`): verify that `summary_el` does not name any
   micro-skill ID string (e.g., `add_1digit`) that is absent from the provided
   context. Since skill IDs follow the pattern `[a-z_]+\d*`, a single regex
   intersection check is sufficient.

**Rationale**: The digit check already present catches numeric hallucinations.
The three new checks close the remaining gaps identified in FR-002 and FR-003
of the spec without adding a language-detection library or LLM self-check loop
(which would double latency).

**Alternatives considered**:
- LLM self-evaluation (ask the model to verify its own output): doubles call
  count and latency; unreliable for 4B models.
- `langdetect` or `lingua` library: adds a new dependency; overkill for a
  stop-word-level heuristic.
- Full semantic similarity check: far too expensive for local single-user use.

---

## R-004: Prompt versioning and rollback strategy

**Decision**: Introduce a `PROMPT_VERSION` config variable (default `"v2"`)
read from `KUMON_PROMPT_VERSION` env var. The prompt registry resolves the
prompts directory as `app/prompts/{PROMPT_VERSION}/`. Setting
`KUMON_PROMPT_VERSION=v1` in `.env` reverts to the previous behaviour with zero
code change.

**Rationale**: The constitution already mandates versioned prompts. Making the
active version an env-var makes rollback trivial and keeps CI testable across
both versions without code duplication.

**Alternatives considered**:
- Hardcoded `v2` path: faster to implement but blocks rollback.
- Per-task-type version: adds complexity with no clear benefit at this scale.

---

## R-005: Retry logic on bad LLM output

**Decision**: Add a single automatic retry in `_call_llm` when the response is
`ERR_LLM_INVALID_JSON` or `ERR_LLM_EMPTY_SUMMARY`. The retry uses the same
prompt with no change. Maximum one retry (two total calls).

**Rationale**: Small models occasionally produce malformed JSON on the first
attempt but succeed on a second attempt with an identical prompt, because
sampling is stochastic (temperature=0.2 is low but not zero). A single retry
catches transient failures at negligible cost (the LLM call is already the
dominant latency). More than one retry would noticeably degrade the CLI
experience.

**Alternatives considered**:
- No retry (current behaviour): causes visible degradation for recoverable
  failures.
- Re-prompt with error context ("your previous response was not valid JSON"):
  effective for larger models; unreliable for 4B models and adds prompt
  engineering complexity.
- Retry count configurable via env-var: over-engineering for a single-user
  local tool.

---

## R-006: Model name discrepancy

**Decision**: Update `config.py` default `LLM_MODEL` to `"Qwen3-4B-MLX-4bit"`
to match the operator's actual model, and update the constitution reference in
the plan. No code logic depends on the model name string beyond passing it to
the API.

**Rationale**: The constitution documents `Qwen3-8B-MLX-4bit` as the reference
model, but the operator is running `Qwen3-4B-MLX-4bit`. The default in config
should reflect operational reality. The constitution's technology section will
be noted as aspirational/minimum; the operator may upgrade later.

**Note**: The constitution update itself is a governance action and is out of
scope for this feature's implementation tasks.


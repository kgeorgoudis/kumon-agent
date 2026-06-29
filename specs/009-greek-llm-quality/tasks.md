---
description: "Task list for feature 009: Improve Greek LLM Response Quality"
---

# Tasks: Improve Greek LLM Response Quality

**Input**: Design documents from `specs/009-greek-llm-quality/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/progress_narrative_v2.md](contracts/progress_narrative_v2.md)

**Organization**: Tasks are grouped by user story. Each phase is independently
testable. No tests were requested in the spec — test tasks are in the Polish
phase only.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: Which user story this task belongs to (US1 / US2 / US3)

---

## Phase 1: Setup

**Purpose**: Create the `v2` prompts directory skeleton so all story phases can
write into it independently.

- [X] T001 Create directory `app/prompts/v2/` (mirrors `app/prompts/v1/` layout)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the prompt-version config var and make the registry
version-aware. Both user story phases 3 and 5 depend on this before the
correct prompt path resolves.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Add `PROMPT_VERSION` config var (env `KUMON_PROMPT_VERSION`, default `"v2"`) to `app/config.py`
- [X] T003 Update `app/agents/prompt_registry.py` to read `cfg.PROMPT_VERSION` and resolve prompts directory as `app/prompts/{PROMPT_VERSION}/` instead of the hardcoded `v1` path

**Checkpoint**: `KUMON_PROMPT_VERSION=v1 uv run kumon progress -c <id>` still works; `KUMON_PROMPT_VERSION=v2` raises a clear "file not found" until Phase 3 completes.

---

## Phase 3: User Story 1 — Grammatically Correct Greek Progress Summaries (Priority: P1) 🎯 MVP

**Goal**: Parent sees clean, grammatically correct Greek sentences when running
`kumon progress -c <child_id>`. The `summary_el` and `rationale_el` fields read
naturally with no syntax errors or English fragments.

**Independent Test**: Run `uv run kumon progress -c <child_id>` and read the
output. The `summary_el` sentence must be complete, in natural Greek, and make
sense to a native speaker without any surrounding English words.

- [X] T004 [P] [US1] Create `app/prompts/v2/kumon_tutor_persona.md` — tighter persona block: explicit `ΜΟΝΟ ελληνικά` rule, shorter constraint list (≤ 6 items), remove duplicate wording from v1
- [X] T005 [P] [US1] Create `app/prompts/v2/progress_summary.md` — revised task prompt with: (a) tighter output constraints referencing the contract in `contracts/progress_narrative_v2.md`, (b) one concrete few-shot example (input payload + expected JSON) using the fictional "Δημήτρης" fixture from the contract, (c) word-limit guidance (`summary_el` ≤ 120 words, `rationale_el` ≤ 2 sentences)

**Checkpoint**: `uv run kumon progress -c <child_id>` with the local model returns a `summary_el` that reads like natural Greek prose. No English fragments. No mid-sentence cutoffs.

---

## Phase 4: User Story 2 — Elimination of Hallucinated Content (Priority: P1)

**Goal**: Every factual claim in the generated narrative is traceable to data
in the deterministic context payload. The agent gracefully rejects and degrades
on responses that contain English text or an empty summary.

**Independent Test**: Inspect `kumon traces show <task_id>`. If the model
produces an English-language response or an empty summary, the trace shows a
machine-readable error code (`ERR_LLM_EMPTY_SUMMARY` or
`ERR_LLM_WRONG_LANGUAGE`) and `narrative_status = "degraded"` — never a
crash.

- [X] T006 [US2] Add `ERR_LLM_EMPTY_SUMMARY` guard to `_validation_node` in `app/agents/agent_graph.py`: if `summary_el` is empty or whitespace-only after generation, set `state["error_code"] = "ERR_LLM_EMPTY_SUMMARY"` and call `_build_progress_fallback`
- [X] T007 [US2] Add `ERR_LLM_WRONG_LANGUAGE` guard to `_validation_node` in `app/agents/agent_graph.py`: use a small frozenset of English stop-words (`{"the", "is", "and", "for", "of", "that", "with", "are"}`) and a regex `\b(the|is|and|for|of|that|with|are)\b` to detect English-language responses; on match set error code and degrade

**Checkpoint**: `kumon traces list --status DEGRADED` shows `ERR_LLM_EMPTY_SUMMARY` or `ERR_LLM_WRONG_LANGUAGE` error codes when triggered, not generic `ERR_LLM_INVALID_JSON`.

---

## Phase 5: User Story 3 — Reliable JSON Output Structure (Priority: P2)

**Goal**: The progress command never crashes or silently swallows a valid
JSON object buried in model output. Transient malformed responses are
auto-retried once before degrading.

**Independent Test**: Manually call `_extract_json_block` with a string that
has a leading `<think>…</think>` block and trailing prose — it must return the
correct dict. Run `kumon progress -c <id>` 5 times; 0 crashes.

- [X] T008 [US3] Rewrite `_extract_json_block` in `app/agents/agent_graph.py`: (1) strip leading `<think>…</think>` block with `re.sub(r'<think>[\s\S]*?</think>', '', raw, flags=re.DOTALL)`, (2) strip markdown fences if present, (3) use `re.search(r'\{[\s\S]*\}', candidate)` to find the outermost JSON object before calling `json.loads`
- [X] T009 [US3] Add single auto-retry in `_call_llm` in `app/agents/agent_graph.py`: if `error_code` is `ERR_LLM_INVALID_JSON` on first attempt, make one identical second call and try extraction again; if second attempt also fails, return the original error code; add a `_retry_count` local variable capped at `1`

**Checkpoint**: Feeding a raw string like `"<think>reasoning here</think>\n\nHere is the JSON:\n\n{\"summary_el\": \"test\"}"` to `_extract_json_block` returns `{"summary_el": "test"}`. Multiple `kumon progress` runs produce no `ERR_LLM_INVALID_JSON` under normal conditions.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests, model-name accuracy, and final verification.

- [X] T010 [P] Create `app/tests/test_greek_quality.py` with: (a) parametric tests asserting `_extract_json_block` handles think-blocks, trailing prose, and plain JSON; (b) a heuristic test loading `app/prompts/v2/progress_summary.md` and asserting the few-shot example validates against the v2 contract schema
- [X] T011 [P] Extend `app/tests/test_agent_graph.py` with: (a) test for `ERR_LLM_EMPTY_SUMMARY` path through `_validation_node`; (b) test for `ERR_LLM_WRONG_LANGUAGE` path; (c) test that a mock returning English text degrades with the correct error code
- [X] T012 [P] Extend `app/tests/test_prompt_registry.py` with: (a) test that `load_prompt_bundle` resolves `v2` prompts when `PROMPT_VERSION="v2"`; (b) test that setting `PROMPT_VERSION="v1"` loads original prompts (rollback smoke-test)
- [X] T013 Update default `LLM_MODEL` in `app/config.py` from `"Qwen3-8B-MLX-4bit"` to `"Qwen3-4B-MLX-4bit"` per research decision R-006 (operator's actual model)

**Checkpoint**: `uv run pytest app/tests/ -v` — all tests green, including T010–T012.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)** and **US2 (Phase 4)**: Both can start after Phase 2; they touch different files and are fully independent
- **US3 (Phase 5)**: Can start after Phase 2; also independent of US1 and US2
- **Polish (Phase 6)**: Depends on Phases 3 + 4 + 5 being complete

### User Story Independence

| Story | Files Changed | Depends On |
|-------|--------------|-----------|
| US1 (Phase 3) | `app/prompts/v2/*.md` | Phase 2 only |
| US2 (Phase 4) | `app/agents/agent_graph.py` (`_validation_node`) | Phase 2 only |
| US3 (Phase 5) | `app/agents/agent_graph.py` (`_extract_json_block`, `_call_llm`) | Phase 2 only |

US1, US2, and US3 can all be worked on in parallel after Phase 2 completes.

### Within Each Story

- T004 and T005 (US1) — parallel (different files)
- T006 → T007 (US2) — sequential (same function)
- T008 → T009 (US3) — sequential (same file, distinct functions)
- T010, T011, T012, T013 (Polish) — all parallel (different files)

---

## Parallel Execution Examples

### After Phase 2 completes — start all three stories simultaneously

```
# US1: Prompt files (parallel within story)
T004: app/prompts/v2/kumon_tutor_persona.md
T005: app/prompts/v2/progress_summary.md

# US2: Validation node (sequential within story)
T006 → T007: app/agents/agent_graph.py (_validation_node)

# US3: Extraction + retry (sequential within story)
T008 → T009: app/agents/agent_graph.py (_extract_json_block, _call_llm)
```

### Polish phase — all parallel

```
T010: app/tests/test_greek_quality.py       (new file)
T011: app/tests/test_agent_graph.py         (extend)
T012: app/tests/test_prompt_registry.py     (extend)
T013: app/config.py                         (model name default)
```

---

## Implementation Strategy

### MVP First (US1 only — Phase 1 + 2 + 3)

1. Complete Phase 1 (T001) — create `v2/` dir
2. Complete Phase 2 (T002 → T003) — config + registry
3. Complete Phase 3 (T004 + T005) — write v2 prompts
4. **STOP and VALIDATE**: `uv run kumon progress -c <child_id>` produces clean Greek
5. If acceptable, proceed to US2 and US3

### Full Incremental Delivery

1. Phase 1 + 2 → foundation ready
2. Phase 3 (US1) → better Greek grammar ← **demo-able MVP**
3. Phase 4 (US2) → hallucination guards active
4. Phase 5 (US3) → JSON robustness + retry
5. Phase 6 → tests green, model name corrected

### Rollback at Any Point

```bash
KUMON_PROMPT_VERSION=v1 uv run kumon progress -c <child_id>
```

This bypasses all v2 prompt changes while keeping the extraction and validation
improvements in place.

---

## Notes

- No new Python dependencies are added
- v1 prompts remain **untouched** throughout — rollback is a one-line env-var change
- T013 (model name default) is cosmetic and can be deferred without affecting functionality
- All three user stories are independently testable immediately after Phase 2


# Contract: Progress Narrative LLM Output (v2)

**Prompt file**: `app/prompts/v2/progress_summary.md`  
**Task type**: `PROGRESS_REPORT`  
**Direction**: LLM → `_reasoning_node` in `agent_graph.py`  
**Format**: Strict JSON (no markdown, no surrounding text)

---

## Input (deterministic context payload)

Passed as the second JSON block in the USER message, after the few-shot example.

```json
{
  "child": {
    "child_id": "<string>",
    "display_name": "<string — Greek child name>"
  },
  "summary": {
    "worksheet_count": "<integer>",
    "date_from": "<ISO 8601 date string or null>",
    "date_to": "<ISO 8601 date string or null>",
    "overall_accuracy_pct": "<float 0–100>",
    "overall_trend": "improving | stable | declining | insufficient_data"
  },
  "skills": [
    {
      "micro_skill_id": "<skill identifier, e.g. add_1digit>",
      "worksheet_count": "<integer>",
      "avg_accuracy_pct": "<float>",
      "last_accuracy_pct": "<float>",
      "trend": "improving | stable | declining | insufficient_data"
    }
  ],
  "points": [
    {
      "instance_id": "<string>",
      "micro_skill_id": "<string>",
      "accuracy_pct": "<float>",
      "confirmed_at": "<ISO 8601 datetime string>"
    }
  ],
  "next_skill_options": {
    "next_skills": [
      {
        "skill_id": "<string>",
        "name_el": "<Greek skill name>",
        "description_el": "<Greek description>",
        "difficulty_level": "<integer>",
        "prerequisites_met": true
      }
    ]
  }
}
```

---

## Output (expected LLM response)

```json
{
  "summary_el": "<2–3 sentence Greek narrative — qualitative, no raw numbers>",
  "suggestions": [
    {
      "target_micro_skill_id": "<skill_id from input skills or next_skills, or null>",
      "suggested_worksheet_type": "drill | mixed_review | correction | concept_reinforcement | timed_fluency | null",
      "rationale_el": "<1–2 sentence Greek rationale grounded in input data>",
      "confidence": "low | medium | high"
    }
  ]
}
```

---

## Field-Level Constraints

### `summary_el`
- Language: Greek (el-GR) only — no English words or phrases
- Length: 2–3 sentences, ≤ 120 words
- Must NOT contain: raw numbers, percentages, or micro-skill ID strings
- Must NOT contain: claims about skills or trends not present in the input
- Tone: encouraging, simple, concrete — appropriate for a parent of a 10-year-old

### `suggestions` array
- Length: 1–2 items (minimum 1, maximum 2)
- `target_micro_skill_id`: MUST be a `micro_skill_id` from `skills[]` OR a `skill_id` from `next_skill_options.next_skills[]`, OR `null`
- `suggested_worksheet_type`: MUST be one of the five enum values or `null`
- `rationale_el`: Greek only, 1–2 sentences, grounded in provided data
- `confidence`: MUST be `"low"`, `"medium"`, or `"high"`

---

## Validation Rules (applied in `_validation_node`)

| Check | Error Code | Action |
|-------|-----------|--------|
| Response cannot be parsed as JSON | `ERR_LLM_INVALID_JSON` | Degrade |
| `summary_el` is empty or whitespace | `ERR_LLM_EMPTY_SUMMARY` | Degrade |
| `summary_el` contains raw digits | `ERR_LLM_CONFLICTING_FACTS` | Degrade |
| `summary_el` contains English stop-words | `ERR_LLM_WRONG_LANGUAGE` | Degrade |
| `suggestions` list is empty | Fallback suggestions injected | `validation_status = "sanitized"` |
| `target_micro_skill_id` not in known skills | Field set to `null` | Silent sanitization |
| `suggested_worksheet_type` not in allowed set | Field set to `null` | Silent sanitization |

---

## Few-Shot Example (embedded in v2 prompt)

The prompt includes one concrete example exchange that demonstrates the expected
output. The example uses a fictional child with two skills to avoid any risk of
leaking real data. The example is placed in the USER turn before the real
payload, clearly delimited.

**Example input payload** (abbreviated):
```json
{
  "child": {"child_id": "demo", "display_name": "Δημήτρης"},
  "summary": {"worksheet_count": 5, "overall_accuracy_pct": 78, "overall_trend": "improving"},
  "skills": [{"micro_skill_id": "add_1digit", "avg_accuracy_pct": 78, "trend": "improving"}],
  "next_skill_options": {"next_skills": [{"skill_id": "add_2digit", "name_el": "Πρόσθεση 2ψήφιων"}]}
}
```

**Example expected output**:
```json
{
  "summary_el": "Ο Δημήτρης βελτιώνεται σταθερά στην πρόσθεση μονοψήφιων αριθμών. Η πρόοδός του δείχνει καλή κατανόηση και αυτοπεποίθηση στις βασικές πράξεις.",
  "suggestions": [
    {
      "target_micro_skill_id": "add_2digit",
      "suggested_worksheet_type": "drill",
      "rationale_el": "Έχει δείξει σταθερή βελτίωση στα μονοψήφια, οπότε μπορεί να δοκιμάσει τα διψήφια με ένα σύντομο εξερευνητικό φύλλο.",
      "confidence": "medium"
    }
  ]
}
```


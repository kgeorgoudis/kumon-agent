# Prompt Maintenance Notes

This directory contains versioned prompt contracts used by the tutor graph.

## Rules

- Keep prompts versioned and reviewable in Git.
- Keep business rules in Python code, not only in prompts.
- Prefer strict JSON schemas for every task-oriented prompt.
- Keep child/parent-facing language Greek-first.
- Do not let prompts restate arithmetic truth that already comes from deterministic code.

## Current prompt set

- `kumon_tutor_persona.md` — shared persona and grounding constraints
- `progress_summary.md` — qualitative progress summary + suggestions
- `worksheet_review.md` — grounded worksheet review output
- `next_step_planning.md` — grounded next-step planning suggestions
- `explain_mistake.md` — short child-friendly mistake explanation

## Updating a prompt

1. Keep the schema backward-compatible when possible.
2. Update or add tests under `app/tests/`.
3. Preserve the parent-advisory tone and deterministic grounding constraints.
4. Record any new prompt file in the relevant spec docs if it changes feature scope.


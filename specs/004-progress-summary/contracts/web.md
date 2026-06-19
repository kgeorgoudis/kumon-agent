# Web Contract: Progress Summary Page

## Route

`GET /progress`

## Purpose

Render a parent-facing Greek progress report page using the same service used by `kumon progress`.

## Query Parameters

- `child` (optional, string): child display name.
- `limit` (optional, int, default: 20): worksheet window size.
- `llm` (optional, bool, default: true): whether to attempt narrative generation.

## Response Semantics

### `200 OK` with report data

Render HTML sections:

1. Child/date-range/report metadata
2. Deterministic metrics cards (overall accuracy, trend, worksheet count)
3. Per-skill performance table
4. Narrative summary panel
5. Next-step suggestions panel

### `200 OK` with no data

Render friendly empty-state message in Greek and CTA to generate/submit first worksheet.

### `200 OK` with LLM degraded mode

Render deterministic report and a warning banner that LLM summary is temporarily unavailable.

### `404` child not found (optional implementation choice)

If route chooses strict child lookup, return a dedicated not-found page in Greek. If route follows soft behavior, return empty-state with child name context.

## Shared-Service Requirement

- Route must call the same progress summary service used by CLI.
- No duplicate aggregation logic in web handlers.


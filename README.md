# Kumon Agent 🧮

A local-first math tutoring system for children, inspired by the Kumon method.
Built for a 10-year-old child in Greece — Greek-first content, printable paper
worksheets, deterministic scoring, and controlled AI assistance.

> **Status**: Milestone 1 — worksheet generation and CLI fully working.
> OCR ingestion, scoring, and mastery tracking come in Milestone 2.

---

## What is the Kumon Method?

Kumon is a self-learning method where exercises are ordered from very easy to
gradually harder, so a child advances through the material mostly on their own.
The key ideas are **small steps**, **daily repetition**, and **accuracy before speed**.

Run `kumon explain method` at any time to read a full parent guide inside the app.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Astral `uv`](https://docs.astral.sh/uv/) (project package manager)

### Install

```bash
git clone <repo-url>
cd kumon-agent
uv sync --dev
```

### Generate your first worksheet

```bash
# List all available skills
uv run kumon list-skills

# Generate a multiplication worksheet (opens in browser, ready to print)
uv run kumon generate multiplication-2-5

# Generate 20 exercises for a named child
uv run kumon profile create "Ελένη" --age 10 --grade 4
uv run kumon generate multiplication-6-9 --child "Ελένη" --exercises 15

# Generate ordering numbers worksheet (deterministic with seed)
uv run kumon generate ordering-numbers --exercises 10 --seed 42 --no-open
```

The worksheet and its answer key are saved as HTML in `output/worksheets/<date>/`.
Open in any browser and print (Cmd+P / Ctrl+P).

## Manual Submission Workflow

Completed worksheets are now ingested manually by the parent (no OCR required).

CLI flow:

```bash
uv run kumon pending
uv run kumon pending --child "Ελένη"
uv run kumon progress --child "Ελένη" --no-llm
uv run kumon progress --child "Ελένη"
uv run kumon submit <instance_id>
uv run kumon submit <instance_id> --answers "1,2,3,4,5" --no-confirm
uv run kumon submit <instance_id> --answers "1,2,3,4,5" --time 12:34 --no-confirm

# Ordering worksheets: separate each exercise answer with ';'
uv run kumon submit <instance_id> --answers "1 3 7 9; 20, 15, 8, 2; 5-6-8-11" --no-confirm
```

Key behavior:

- ✅ Recover worksheet IDs after terminal restart with `kumon pending`
- ✅ Greek progress report with deterministic metrics via `kumon progress`
- ✅ Optional LLM narrative + suggestions with graceful fallback
- ✅ Interactive one-by-one answer entry
- ✅ Bulk answer entry with `--answers`
- ✅ Ordering-sheet bulk entry with semicolon (`;`) exercise separators
- ✅ Review/correction loop before confirmation
- ✅ Optional timing capture with `--time`
- ✅ Deterministic scoring with audit trail (`worksheet -> submission -> score`)
- ✅ Local-only operation (no OCR, no vision model, no remote dependency)

Latest submission regression run (2026-06-17):

```bash
uv run pytest app/tests/test_submission_service.py app/tests/test_cli_submit.py -q
```

Result: `30 passed`

---

## CLI Reference

```
kumon --help

Commands:
  generate              Generate a printable worksheet and its answer key
  list-skills           List all available micro-skills
  history               Show recent worksheets
  pending               Show worksheets pending submission
  progress              Show child progress summary and suggestions
  profile create        Create or update a child profile
  profile list          List saved profiles
  profile show          Show a profile's details
  explain method        Explain the Kumon method (parent guide)
  explain skill         Describe a skill and its micro-skills
  explain progression   Explain the progression rules
  explain worksheet-types  Describe each worksheet type
```

### generate options

```
kumon generate <skill> [OPTIONS]

Arguments:
  skill           Micro-skill ID (e.g. multiplication-2-5, addition-with-carrying)

Options:
  -n, --exercises INT    Number of exercises (default: 15)
  -c, --child TEXT       Child display name (must match a saved profile)
  --seed INT             Fixed random seed for reproducible worksheets
  --type TEXT            Worksheet type: drill | mixed-review | timed-fluency
  --open / --no-open     Open in browser after generating (default: --open)
```

### Available micro-skills

| Skill ID | Greek Name | Category | Level |
|----------|-----------|----------|-------|
| `addition-single-digit` | Πρόσθεση Μονοψήφιων | Addition | 1 |
| `addition-two-digit-no-carry` | Πρόσθεση Διψήφιων | Addition | 2 |
| `addition-with-carrying` | Πρόσθεση με Κρατούμενο | Addition | 3 |
| `addition-three-numbers` | Πρόσθεση Τριών Αριθμών | Addition | 4 |
| `subtraction-single-digit` | Αφαίρεση Μονοψήφιων | Subtraction | 1 |
| `subtraction-two-digit-no-borrow` | Αφαίρεση Διψήφιων | Subtraction | 2 |
| `subtraction-with-borrowing` | Αφαίρεση με Δανεισμό | Subtraction | 3 |
| `half-and-double` | Μισό και Διπλό | Number Sense | 1 |
| `ordering-numbers` | Διάταξη Αριθμών | Number Sense | 2 |
| `multiplication-2-5` | Πολλαπλασιασμός 2–5 | Multiplication | 4 |
| `multiplication-6-9` | Πολλαπλασιασμός 6–9 | Multiplication | 6 |
| `multiplication-mixed` | Μεικτοί Πίνακες 2–9 | Multiplication | 7 |
| `division-2-5` | Διαίρεση 2–5 | Division | 5 |
| `division-6-9` | Διαίρεση 6–9 | Division | 7 |
| `division-mixed` | Μεικτή Διαίρεση | Division | 8 |

---

## Architecture

```
app/
├── config.py               # Runtime config (paths, LLM endpoint, defaults)
├── domain/
│   ├── models.py           # Pydantic domain entities (Exercise, ChildProfile, …)
│   ├── knowledge_base.py   # Embedded Kumon documentation (explain commands)
│   └── math_engine.py      # Deterministic arithmetic problem generation
├── services/
│   ├── worksheet_generator.py  # Orchestrates generation + HTML rendering
│   ├── progress_summary_service.py  # Deterministic report + tutor graph facade
│   ├── worksheet_review_service.py  # Grounded worksheet review facade
│   └── tutor_planning_service.py    # Grounded next-step planning facade
├── persistence/
│   └── database.py         # SQLite storage + agent run/step traces
├── templates/
│   ├── worksheet.html.j2   # Printable worksheet template (Greek, A4)
│   └── answer_key.html.j2  # Answer key template
├── agents/
│   ├── llm_client.py       # Local LLM client (OpenAI-compatible)
│   ├── agent_graph.py      # LangGraph tutor orchestration
│   ├── tools.py            # Deterministic tool wrappers
│   └── traces.py           # Agent run/step trace helpers
├── prompts/v1/
│   ├── progress_summary.md     # Tutor progress narrative contract
│   ├── worksheet_review.md     # Tutor worksheet review contract
│   ├── next_step_planning.md   # Tutor planning contract
│   └── explain_mistake.md      # Versioned LLM prompt
├── cli/
│   └── main.py             # Typer CLI (entry point: `kumon`)
├── api/                    # FastAPI stub (Milestone 2+)
└── tests/                  # pytest test suite (includes LangGraph regressions)
```

### Key design decisions

| Decision | Why |
|----------|-----|
| All arithmetic by Python, never the LLM | LLM answers are unreliable for math |
| Jinja2 HTML output | No PDF dependencies; browser print is excellent |
| SQLite + raw sqlite3 | Zero extra dependencies, easy to inspect |
| Fixed random seed stored | Worksheets can be regenerated identically |
| Greek strings separate from code | Code/logs stay in English; content in Greek |
| LangGraph for tutor orchestration | Explicit state/steps/tools without moving arithmetic truth into prompts |

---

## Local LLM Configuration

The app uses a local LLM (Qwen3-8B-MLX-4bit) for optional tutor tasks only
(progress summaries, worksheet review language, next-step advice). These
tasks run through a LangGraph orchestration layer that is grounded in
deterministic Python data and degrades gracefully when the model is offline.
The core worksheet loop works **without** the LLM.

Default endpoint: `http://127.0.0.1:8000/v1`

Override with environment variables:

```bash
export KUMON_LLM_BASE_URL="http://127.0.0.1:8000/v1"
export KUMON_LLM_MODEL="Qwen3-8B-MLX-4bit"
```

---

## Configuration

All defaults are in `app/config.py` and can be overridden with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `KUMON_LLM_BASE_URL` | `http://127.0.0.1:8000/v1` | Local LLM endpoint |
| `KUMON_LLM_MODEL` | `Qwen3-8B-MLX-4bit` | Model name |
| `KUMON_EXERCISE_COUNT` | `15` | Default exercises per worksheet |
| `KUMON_CHILD_NAME` | `Μαθητής` | Default child name |
| `KUMON_CHILD_AGE` | `10` | Default child age |
| `KUMON_CHILD_GRADE` | `4` | Default grade level |

---

## Running Tests

```bash
uv run pytest                    # all tests
uv run pytest -v                 # verbose
uv run pytest app/tests/test_math_engine.py -v   # specific file
uv run pytest --cov             # with coverage report
```

## Web Progress Page

Once the API server is running, open:

```bash
http://127.0.0.1:8000/progress
http://127.0.0.1:8000/progress?child=Ελένη
http://127.0.0.1:8000/progress?child=Ελένη&llm=false
```

The page uses the same shared service payload as `kumon progress`.

### Test Coverage Summary (v0.1.0)

**Status**: ✅ **63/63 tests passing** (latest run, fully offline)

| Category | Tests | Status | Notes |
|----------|-------|--------|-------|
| Math Engine | 18 | ✅ Pass | Deterministic arithmetic, seeding, all operations |
| Worksheet Generation | 10 | ✅ Pass | HTML rendering, Greek content, reproducibility |
| Persistence (SQLite) | 9 | ✅ Pass | Profile CRUD, worksheet storage, idempotency |
| OCR Ingestion | 5 | ✅ Pass | Validation, OCR field persistence, threshold triage |
| OCR Review | 5 | ✅ Pass | Review table, manual corrections, approve transitions |
| Rescoring | 5 | ✅ Pass | Deterministic hash, idempotence, snapshot reuse |
| CLI Contracts | 5 | ✅ Pass | ingest/review/correct/approve/rescore output behavior |
| Integration | — | ✅ Pass | CLI workflows across worksheet + OCR lifecycle |

**Test principles**:
- All tests are deterministic and run offline (no network/LLM required)
- Domain logic tests in `test_math_engine.py` verify arithmetic correctness
- Service tests in `test_worksheet_generator.py` verify HTML output and Greek text
- Persistence tests in `test_database.py` verify SQLite correctness
- Tests use fixtures for reproducible test data

---

## Milestones

| Milestone | Status | Description |
|-----------|--------|-------------|
| **1** | ✅ Done | Domain models, math engine, worksheet generation, CLI |
| 2 | 🔲 Planned | Photo upload, OCR ingestion, OCR review, scoring engine |
| 3 | 🔲 Planned | Mastery tracking, progression planner, parent dashboard |
| 4 | 🔲 Planned | LLM explanations in Greek, evaluation harness |

---

## In-App Help

Because you're not a Kumon expert, the app has documentation built in:

```bash
kumon explain method                  # What is Kumon, how does it work
kumon explain skill multiplication    # Explain a skill in Greek
kumon explain progression             # When does the app advance / step back
kumon explain worksheet-types         # Drill vs mixed review vs correction
kumon list-skills --verbose           # All skills with Greek descriptions
```

---

## Constitutional Principles

This project follows a [written constitution](.specify/memory/constitution.md):

1. **Deterministic before agentic** — rules in Python, not prompts
2. **Arithmetic truth from code** — the LLM never computes answers
3. **Inspectable progression decisions** — every progression action is explainable
4. **Parent override authority** — the parent controls everything
5. **Paper workflow first** — generate → print → solve → scan → score
6. **Short and incremental** — 10–15 exercises, one micro-skill at a time
7. **Greek-first content** — child/parent UI in Greek; code in English
8. **Local-first architecture** — LLM and DB run locally by default
9. **Shared domain logic** — CLI and web call the same services
10. **In-app documentation** — Kumon docs accessible from CLI and web
11. **Kumon tutor persona** — LLM tutoring tasks follow versioned tutor prompts
12. **Agent observability and traceability** — tutor runs emit inspectable traces

---

## Release Notes — v0.1.0 (Milestone 1)

**Released**: 2026-06-14 | **Branch**: `master` | **Status**: ✅ Production Ready

### What's Included

✅ **Worksheet Generation Loop**
- Generate deterministic math exercises for 14+ micro-skills
- Export printable worksheet + answer key as HTML (A4, Greek-friendly)
- Reproducible generation with seed support
- Support for 15–40 exercises per worksheet

✅ **In-Application Learning Guides**
- Embedded Kumon method overview for parents
- Skill descriptions and difficulty progression system
- Progression rules documentation
- Worksheet type explanations
- No external dependencies (all docs locally embedded)

✅ **Local Profile & History Management**
- Create and manage child profiles (name, age, grade, preferences)
- Store worksheet generation history locally
- Query history by child or micro-skill
- SQLite-based persistence (no cloud sync)

✅ **CLI Interface**
- `kumon generate <skill>` — print-ready worksheets
- `kumon list-skills` — browse available skills
- `kumon explain` — access embedded documentation
- `kumon profile` — manage child settings
- `kumon history` — view past worksheets

✅ **Deterministic Quality**
- 39/39 offline tests passing (0.22s)
- Arithmetic always correct (Python-computed, never LLM)
- Reproducible worksheets (seed-based)
- Local-first architecture (zero cloud dependencies)

### What's NOT Included (Milestone 2+)

❌ **Not in v0.1.0**:
- Photo/PDF upload and OCR (Milestone 2)
- Worksheet scoring engine (M2)
- Mastery tracking and state detection (M3)
- Progression planner / auto-level-up (M3)
- Web dashboard and visualisations (M3)
- LLM-powered mistake explanations in Greek (M4)

❌ **Known Limitations**:
- No support for timed worksheets (template ready, logic pending M3)
- No OCR review UI — OCR comes in M2 with dedicated ingestion workflow
- No parent override recording — framework ready, UI comes in M3
- No evaluation harness for progression quality (M4)

### Installation & Use

```bash
uv sync --dev
uv run kumon generate multiplication-2-5
uv run kumon history
uv run pytest -v
```

### Backwards Compatibility

v0.1.0 establishes the baseline API. Future versions will maintain:
- CLI command syntax (additions only, no breaking changes in v1.x)
- SQLite schema versioning (migrations will be additive)
- Worksheet HTML structure for print compatibility
- Python 3.12+ minimum

### Contributors & Attribution

Built by K. Georgoudis for local tutoring of a 10-year-old child in Greece.
Inspired by the Kumon Institute of Education self-learning methodology.
Follows a written [constitution](.specify/memory/constitution.md) for governance.

### Getting Help

```bash
uv run kumon --help
uv run kumon explain method    # Kumon method overview
uv run kumon explain skill multiplication   # Skill details
uv run kumon list-skills --verbose          # All skills with descriptions
```

See [README.md](README.md) and `.specify/memory/constitution.md` for deeper context.

### Next Steps (Roadmap)

- **v0.2.0 (M2)**: Manual submission workflow → deterministic scoring → progress summary
- **v0.3.0 (M3)**: Mastery tracking → progression planner → parent dashboard
- **v0.4.0 (M4)**: LLM-powered explanations in Greek, evaluation harness

### Trace inspection and diagnostics

When tutor orchestration runs are persisted locally, you can inspect and filter them from the CLI or HTTP API:

```bash
# List recent traces with optional filters
uv run kumon traces list                                   # All recent runs
uv run kumon traces list --status DEGRADED                 # Degraded runs only
uv run kumon traces list --status FAILED                   # Failed runs only
uv run kumon traces list --type PROGRESS_REPORT            # Filter by task type
uv run kumon traces list --hours 6 --limit 10              # Last 6 hours, max 10
uv run kumon traces list --status DEGRADED --json          # Machine-readable JSON

# Advanced filtering with the filter alias
uv run kumon traces filter --status DEGRADED --type WORKSHEET_REVIEW

# Show a single run and its ordered step timeline
uv run kumon traces show <task_id>
uv run kumon traces show <task_id> --json                  # Full JSON trace detail
```

The same data is available from the local API (when the server is running):

```bash
# Start the API server
uv run uvicorn app.api:api --reload

# Query via HTTP
curl "http://127.0.0.1:8000/api/v1/traces"
curl "http://127.0.0.1:8000/api/v1/traces?status=DEGRADED&hours=6"
curl "http://127.0.0.1:8000/api/v1/traces/<task_id>"
curl "http://127.0.0.1:8000/api/v1/traces/<task_id>/steps"
```

Traces are sanitized at write time and **never** contain child PII, full LLM prompts, or secrets.
See [`specs/008-agent-observability/quickstart.md`](specs/008-agent-observability/quickstart.md) for full operator documentation including error code reference and troubleshooting.

---

"""
Kumon Agent — local-first math tutoring system for children.

Architecture Overview
---------------------
The application follows a layered, domain-driven design that separates concerns
and ensures the business logic (deterministic scoring, progression, mastery)
remains independent of transport and UI layers.

Layers (bottom to top):
1. Domain (`domain/`): Pure Python, no framework dependencies. Models, rules,
   arithmetic engines. Constitutional Principle II: Arithmetic truth from code.

2. Persistence (`persistence/`): SQLite storage, append-only events, no hidden mutable state.
   Constitutional Principle VIII: Local-first.

3. Services (`services/`): Orchestration over domain + persistence. Called by both
   CLI and future web API. Constitutional Principle IX: Shared domain logic.

4. Transport (`cli/`, `api/`, `web/`): Thin entry points. Route to services.
   Constitutional Principle V: Paper workflow first, CLI second, web third.

5. Agents (`agents/`, `prompts/`): Bounded LLM orchestration for ambiguous,
   non-deterministic tasks only (explaining mistakes, summarizing results).
   Constitutional Principle I: Deterministic before agentic.

6. Supporting (`templates/`, `config.py`): Rendering and configuration.

Constitutional Principles Encoded
----------------------------------
I.   Deterministic Before Agentic     ← agents/ isolated to non-core tasks
II.  Arithmetic Truth From Code       ← domain/math_engine.py only source
III. Inspectable Progression          ← records kept, machine-readable (future)
IV.  Parent Override Authority        ← audit trail ready (Milestone 3+)
V.   Paper Workflow First             ← CLI mirrors paper loop, API is secondary
VI.  Short & Incremental Assignments  ← default 15 exercises, configurable
VII. Greek-First Content              ← child-facing strings all Greek
VIII.Local-First Architecture         ← SQLite locally, LLM at 127.0.0.1:8000
IX.  Shared Domain Logic              ← services/ layer shared by all transports
X.   In-App Documentation             ← KnowledgeBase embedded, not README-only

Milestone Roadmap
-----------------
M1 (v0.1.0 ✅ DONE)      → Worksheet generation, in-app docs, local profiles
M2 (v0.2.0 ✅ DONE)      → Manual submission, scoring engine, mastery tracking
M3 (v0.3.0 PLANNED)      → Progression planner, parent dashboard
M4 (v0.4.0 PLANNED)      → LLM explanations in Greek, evaluation harness

Testing Strategy
----------------
- Unit tests for all domain logic (deterministic rules, math engine)
- Integration tests for service orchestration and I/O
- Fixture-based tests for worksheet parsing and scoring
- Regression tests for past bugs
- All tests are offline, require no external services

Development Notes
-----------------
- See .specify/memory/constitution.md for governance and amendment rules
- See AGENTS.md for product goals and non-goals
- See specs/001-build-first-working/ for v1 feature specification and tasks
- See README.md for CLI usage and quickstart
"""

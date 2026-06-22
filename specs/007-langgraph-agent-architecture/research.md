# Research: LangGraph Agentic Architecture

**Feature**: `007-langgraph-agent-architecture`
**Date**: 2026-06-22

## Decision 1: Use a single LangGraph state graph per tutor responsibility

- **Decision**: Model each LLM-assisted tutor responsibility as a small LangGraph `StateGraph` that shares one typed state object and a fixed set of step nodes.
- **Rationale**: The feature asks for agentic principles and LangGraph structure. A state graph makes the control flow explicit, keeps branching inspectable, and preserves deterministic step ordering for tests.
- **Alternatives considered**:
  - Direct `chat.completions` calls inside services: rejected because it keeps orchestration implicit and hard to inspect.
  - A generic agent loop with ad-hoc tool selection: rejected because it weakens reproducibility and makes step boundaries unclear.

## Decision 2: Keep deterministic truth in existing services and expose them as tools

- **Decision**: Wrap existing deterministic services (`progress_summary_service`, `progression_service`, `scoring_service`, and relevant domain helpers) as LangGraph tools instead of moving logic into prompts.
- **Rationale**: The constitution requires arithmetic and progression truth to remain code-owned. Tools provide the agent with grounded facts while keeping tests focused on Python logic.
- **Alternatives considered**:
  - Reimplementing scoring/progression inside agent nodes: rejected because it duplicates logic and risks drift.
  - Letting the LLM infer values from raw worksheet data: rejected because it is unreliable and violates deterministic truth.

## Decision 3: Use structured outputs for all model-facing tasks

- **Decision**: Continue using versioned prompts in `app/prompts/v1/` and validate model responses with Pydantic/JSON schemas before turning them into user-facing text.
- **Rationale**: Structured outputs keep the graph deterministic at the control-flow layer, make fallback handling easier, and let tests assert schema compliance.
- **Alternatives considered**:
  - Free-form natural language outputs: rejected because they are harder to validate and more fragile under failures.
  - Inline prompt strings in Python code: rejected because prompts need versioning and reviewable diffs.

## Decision 4: Degrade to deterministic-only output when the model fails

- **Decision**: Treat network errors, timeouts, invalid JSON, truncation, or schema failures as non-fatal narrative failures and return deterministic output with a degraded status.
- **Rationale**: Offline-first operation must not be blocked by the model. The core worksheet and progress workflows must keep working even when the tutor narrative is unavailable.
- **Alternatives considered**:
  - Raising an exception to the user: rejected because it blocks the parent workflow.
  - Silently dropping failures: rejected because the operator needs an explicit degraded status.

## Decision 5: Keep the public interface thin and shared

- **Decision**: Keep CLI and FastAPI handlers as thin entry points that call shared services/agent facades, not graph internals directly.
- **Rationale**: The project already follows shared-domain logic principles. This preserves testability and keeps the agent layer reusable from both CLI and web.
- **Alternatives considered**:
  - Creating separate CLI and API agent paths: rejected because it would duplicate orchestration and increase drift risk.
  - Moving business logic into route handlers: rejected because it violates the shared service architecture.

## Decision 6: Add lightweight run/step traces for inspectability

- **Decision**: Persist or emit structured run/step metadata for each agent execution, including prompt version, step name, status, and high-level inputs/outputs.
- **Rationale**: The spec explicitly requires inspectable, versioned behavior. Minimal traces are enough to explain what the tutor did without logging sensitive raw content unnecessarily.
- **Alternatives considered**:
  - Relying on application logs alone: rejected because logs are too noisy and not structured enough for review.
  - Building a full observability stack now: rejected because it is heavier than needed for this iteration.


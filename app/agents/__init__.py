"""
Agents layer — LangGraph orchestration for LLM-assisted tasks.

Constitutional boundaries
-------------------------
Good uses of the LLM (Constitutional Principle I):
  - Explain a mistake in simple Greek
  - Summarise a worksheet result for the parent
  - Draft next-step rationale

Bad uses (prohibited):
  - Compute arithmetic answers
  - Make progression decisions without deterministic rules
  - Replace the scoring engine
"""

from app.agents.agent_graph import ProgressGraphState, create_progress_task, create_task, run_progress_graph, run_tutor_graph
from app.agents.prompt_registry import get_prompt_paths, get_prompt_version, load_prompt_bundle
from app.agents.state import (
    TutorOutcome,
    TutorStepStatus,
    TutorStepTrace,
    TutorTaskState,
    TutorTaskStatus,
    TutorTaskType,
)

__all__ = [
    "ProgressGraphState",
    "TutorOutcome",
    "TutorStepStatus",
    "TutorStepTrace",
    "TutorTaskState",
    "TutorTaskStatus",
    "TutorTaskType",
    "create_progress_task",
    "create_task",
    "get_prompt_paths",
    "get_prompt_version",
    "load_prompt_bundle",
    "run_progress_graph",
    "run_tutor_graph",
]


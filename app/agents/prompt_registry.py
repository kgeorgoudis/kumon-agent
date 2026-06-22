"""Prompt registry for tutor orchestration task types."""

from __future__ import annotations

from pathlib import Path

from app.agents.state import TutorTaskType

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "v1"
_PERSONA_FILE = "kumon_tutor_persona.md"

_TASK_PROMPT_FILES: dict[TutorTaskType, str] = {
    TutorTaskType.PROGRESS_REPORT: "progress_summary.md",
    TutorTaskType.WORKSHEET_REVIEW: "worksheet_review.md",
    TutorTaskType.NEXT_STEP_PLANNING: "next_step_planning.md",
}


def get_prompt_paths(task_type: TutorTaskType) -> tuple[Path, Path]:
    """Return persona and task prompt file paths for a task type."""
    task_file = _TASK_PROMPT_FILES.get(task_type)
    if task_file is None:
        raise ValueError(f"Unsupported tutor task type: {task_type}")
    return _PROMPTS_DIR / _PERSONA_FILE, _PROMPTS_DIR / task_file


def load_prompt_bundle(task_type: TutorTaskType) -> tuple[str, str]:
    """Load persona prompt and task prompt content."""
    persona_path, task_path = get_prompt_paths(task_type)
    return persona_path.read_text(encoding="utf-8").strip(), task_path.read_text(encoding="utf-8").strip()


def get_prompt_version(task_type: TutorTaskType) -> str:
    """Return the prompt version token used in run metadata."""
    _, task_path = get_prompt_paths(task_type)
    return f"v1/{task_path.stem}"


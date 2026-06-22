from __future__ import annotations

from app.agents.prompt_registry import get_prompt_paths, get_prompt_version, load_prompt_bundle
from app.agents.state import TutorTaskType


def test_prompt_registry_resolves_versioned_paths():
    persona_path, task_path = get_prompt_paths(TutorTaskType.PROGRESS_REPORT)
    assert persona_path.name == "kumon_tutor_persona.md"
    assert task_path.name == "progress_summary.md"
    assert get_prompt_version(TutorTaskType.PROGRESS_REPORT) == "v1/progress_summary"


def test_prompt_registry_loads_bundles_for_all_task_types():
    for task_type in TutorTaskType:
        persona, task_prompt = load_prompt_bundle(task_type)
        assert persona
        assert task_prompt


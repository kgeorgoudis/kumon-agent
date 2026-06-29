from __future__ import annotations

import app.config as cfg
from app.agents.prompt_registry import get_prompt_paths, get_prompt_version, load_prompt_bundle
from app.agents.state import TutorTaskType


def test_prompt_registry_resolves_versioned_paths():
    persona_path, task_path = get_prompt_paths(TutorTaskType.PROGRESS_REPORT)
    assert persona_path.name == "kumon_tutor_persona.md"
    assert task_path.name == "progress_summary.md"
    assert get_prompt_version(TutorTaskType.PROGRESS_REPORT) == f"{cfg.PROMPT_VERSION}/progress_summary"


def test_prompt_registry_loads_bundles_for_all_task_types():
    for task_type in TutorTaskType:
        persona, task_prompt = load_prompt_bundle(task_type)
        assert persona
        assert task_prompt


def test_prompt_registry_v2_is_default():
    """Active prompt version matches PROMPT_VERSION config (default v2)."""
    import app.config as cfg
    version = get_prompt_version(TutorTaskType.PROGRESS_REPORT)
    assert version.startswith(cfg.PROMPT_VERSION + "/")


def test_prompt_registry_v1_rollback(monkeypatch):
    """Setting PROMPT_VERSION=v1 loads original prompts without any code change."""
    import app.config as cfg
    monkeypatch.setattr(cfg, "PROMPT_VERSION", "v1")
    persona, task_prompt = load_prompt_bundle(TutorTaskType.PROGRESS_REPORT)
    assert persona  # v1 persona loads successfully
    assert task_prompt  # v1 task prompt loads successfully
    version = get_prompt_version(TutorTaskType.PROGRESS_REPORT)
    assert version == "v1/progress_summary"


def test_prompt_registry_v2_progress_summary_differs_from_v1(monkeypatch):
    """v2 progress_summary.md must differ from v1 (contains the few-shot example)."""
    import app.config as cfg
    monkeypatch.setattr(cfg, "PROMPT_VERSION", "v1")
    _, v1_task = load_prompt_bundle(TutorTaskType.PROGRESS_REPORT)

    monkeypatch.setattr(cfg, "PROMPT_VERSION", "v2")
    _, v2_task = load_prompt_bundle(TutorTaskType.PROGRESS_REPORT)

    assert v1_task != v2_task, "v2 progress prompt must be different from v1"
    # v2 must contain the few-shot example marker
    assert "Δημήτρης" in v2_task or "summary_el" in v2_task

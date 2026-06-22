"""Shared pytest fixtures for agent orchestration tests."""

from types import SimpleNamespace
from typing import Optional

import pytest


class _FakeChoice:
    def __init__(self, content: str, finish_reason: Optional[str] = "stop") -> None:
        self.message = SimpleNamespace(content=content)
        self.finish_reason = finish_reason


class FakeChatCompletions:
    def __init__(self, content: str, finish_reason: Optional[str] = "stop", should_raise: bool = False) -> None:
        self._content = content
        self._finish_reason = finish_reason
        self._should_raise = should_raise

    def create(self, **_: object):
        if self._should_raise:
            raise RuntimeError("LLM unavailable")
        return SimpleNamespace(choices=[_FakeChoice(self._content, self._finish_reason)])


class FakeLLMClient:
    def __init__(self, content: str, finish_reason: Optional[str] = "stop", should_raise: bool = False) -> None:
        self.chat = SimpleNamespace(
            completions=FakeChatCompletions(content, finish_reason=finish_reason, should_raise=should_raise)
        )


@pytest.fixture
def fake_json_llm_response() -> str:
    return (
        '{"summary_el":"Σταθερή πρόοδος.",'
        '"suggestions":[{"target_micro_skill_id":"addition_single_digit",'
        '"suggested_worksheet_type":"drill",'
        '"rationale_el":"Συνεχίστε με μικρά βήματα.",'
        '"confidence":"medium"}]}'
    )


@pytest.fixture
def make_fake_llm_client():
    def _factory(content: str, finish_reason: Optional[str] = "stop", should_raise: bool = False):
        return FakeLLMClient(content, finish_reason=finish_reason, should_raise=should_raise)

    return _factory



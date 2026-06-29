"""Tests for Greek LLM quality improvements — feature 009.

Covers:
- _extract_json_block robustness (think-blocks, trailing prose, fences, plain JSON)
- v2 progress_summary prompt contains the required few-shot example structure
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.agent_graph import _extract_json_block


# ── _extract_json_block extraction tests ──────────────────────────────────────

class TestExtractJsonBlock:
    def test_plain_json(self):
        raw = '{"summary_el": "Καλή πρόοδος.", "suggestions": []}'
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Καλή πρόοδος."

    def test_markdown_fenced_json(self):
        raw = '```json\n{"summary_el": "Βελτίωση.", "suggestions": []}\n```'
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Βελτίωση."

    def test_think_block_stripped(self):
        raw = (
            "<think>Let me think about this carefully...</think>\n\n"
            '{"summary_el": "Σταθερή πρόοδος.", "suggestions": []}'
        )
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Σταθερή πρόοδος."

    def test_think_block_with_multiline_content(self):
        raw = (
            "<think>\nStep 1: analyse data\nStep 2: write summary\n</think>\n"
            '{"summary_el": "Καλές επιδόσεις.", "suggestions": []}'
        )
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Καλές επιδόσεις."

    def test_trailing_prose_ignored(self):
        raw = (
            '{"summary_el": "Η πρόοδος είναι καλή.", "suggestions": []}'
            "\n\nHope this helps!"
        )
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Η πρόοδος είναι καλή."

    def test_json_embedded_in_prose(self):
        raw = (
            "Here is the JSON output:\n\n"
            '{"summary_el": "Ανοδική τάση.", "suggestions": []}'
            "\n\nLet me know if you need anything else."
        )
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Ανοδική τάση."

    def test_think_block_followed_by_fenced_json(self):
        raw = (
            "<think>reasoning</think>\n"
            "```json\n"
            '{"summary_el": "Πολύ καλά!", "suggestions": []}\n'
            "```"
        )
        result = _extract_json_block(raw)
        assert result["summary_el"] == "Πολύ καλά!"

    def test_raises_on_completely_invalid_input(self):
        with pytest.raises(Exception):
            _extract_json_block("This is just plain text with no JSON at all.")


# ── v2 progress_summary prompt structure check ────────────────────────────────

_V2_PROGRESS_PROMPT = (
    Path(__file__).resolve().parent.parent / "prompts" / "v2" / "progress_summary.md"
)


def test_v2_progress_summary_prompt_exists():
    assert _V2_PROGRESS_PROMPT.exists(), "v2/progress_summary.md must exist"


def test_v2_progress_summary_contains_few_shot_example():
    content = _V2_PROGRESS_PROMPT.read_text(encoding="utf-8")
    # Must contain a JSON block with the required output fields
    assert "summary_el" in content
    assert "suggestions" in content
    assert "rationale_el" in content


def test_v2_progress_summary_few_shot_example_is_valid_json():
    """The inline example JSON in the prompt must be parseable."""
    content = _V2_PROGRESS_PROMPT.read_text(encoding="utf-8")
    # Find the example output line (single-line JSON starting with {"summary_el":)
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('{"summary_el":'):
            parsed = json.loads(line)
            assert "summary_el" in parsed
            assert "suggestions" in parsed
            assert isinstance(parsed["suggestions"], list)
            assert len(parsed["suggestions"]) >= 1
            suggestion = parsed["suggestions"][0]
            assert "rationale_el" in suggestion
            assert "confidence" in suggestion
            return
    pytest.fail("No inline few-shot output example found in v2/progress_summary.md")


def test_v2_progress_summary_enforces_greek_only():
    content = _V2_PROGRESS_PROMPT.read_text(encoding="utf-8")
    # The prompt must contain an explicit Greek-only instruction
    assert "ΜΟΝΟ" in content or "ελληνικά" in content, (
        "v2/progress_summary.md must contain an explicit Greek-only instruction"
    )


def test_v2_persona_prompt_exists():
    persona_path = _V2_PROGRESS_PROMPT.parent / "kumon_tutor_persona.md"
    assert persona_path.exists()


def test_v2_persona_enforces_greek_only():
    persona_path = _V2_PROGRESS_PROMPT.parent / "kumon_tutor_persona.md"
    content = persona_path.read_text(encoding="utf-8")
    assert "ΜΟΝΟ" in content and "ελληνικά" in content


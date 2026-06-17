"""
Tests for app/services/worksheet_generator.py

These tests verify the worksheet generation pipeline without hitting the
filesystem (by overriding cfg.WORKSHEETS_DIR to a tmp_path).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import ChildProfile, MicroSkillId, WorksheetType
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def tmp_output(tmp_path: Path, monkeypatch):
    """Redirect all worksheet output to a pytest tmp_path."""
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def sample_child() -> ChildProfile:
    return ChildProfile(
        child_id="test-child",
        display_name="Ελένη",
        age=10,
        grade_level=4,
        preferred_sheet_length=10,
    )


# ── Worksheet instance ────────────────────────────────────────────────────────


def test_generate_worksheet_returns_instance(tmp_output, sample_child):
    instance = generate_worksheet(
        MicroSkillId.MULTIPLICATION_2_5,
        child=sample_child,
        seed=1,
    )
    assert instance.instance_id
    assert instance.micro_skill_id == MicroSkillId.MULTIPLICATION_2_5
    assert len(instance.exercises) == sample_child.preferred_sheet_length


def test_explicit_count_overrides_profile(tmp_output, sample_child):
    instance = generate_worksheet(
        MicroSkillId.ADDITION_SINGLE_DIGIT,
        child=sample_child,
        count=7,
        seed=0,
    )
    assert len(instance.exercises) == 7


def test_seed_is_recorded(tmp_output):
    instance = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, seed=42)
    assert instance.seed == 42


def test_reproducible_with_same_seed(tmp_output):
    a = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, count=5, seed=7)
    b = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, count=5, seed=7)
    assert [ex.problem_text for ex in a.exercises] == [ex.problem_text for ex in b.exercises]


# ── File output ───────────────────────────────────────────────────────────────


def test_html_files_are_created(tmp_output, sample_child):
    instance = generate_worksheet(
        MicroSkillId.MULTIPLICATION_6_9,
        child=sample_child,
        seed=3,
    )
    assert instance.html_path is not None
    assert Path(instance.html_path).exists(), "Worksheet HTML file not created"
    assert instance.answer_key_path is not None
    assert Path(instance.answer_key_path).exists(), "Answer key HTML file not created"


def test_worksheet_html_contains_greek_title(tmp_output):
    instance = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, seed=0)
    html = Path(instance.html_path).read_text(encoding="utf-8")
    assert "Πολλαπλασιασμός" in html


def test_worksheet_html_contains_exercises(tmp_output):
    instance = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=10, seed=0)
    html = Path(instance.html_path).read_text(encoding="utf-8")
    # All exercises should appear as problem text
    for ex in instance.exercises:
        assert "___" in html  # blank answer slots


def test_answer_key_html_contains_answers(tmp_output):
    instance = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, count=5, seed=0)
    html = Path(instance.answer_key_path).read_text(encoding="utf-8")
    # Answers should appear (no blanks in answer key)
    for ex in instance.exercises:
        assert str(int(ex.answer)) in html


def test_answer_key_not_same_as_worksheet(tmp_output):
    instance = generate_worksheet(MicroSkillId.MULTIPLICATION_2_5, count=5, seed=0)
    ws_html = Path(instance.html_path).read_text(encoding="utf-8")
    key_html = Path(instance.answer_key_path).read_text(encoding="utf-8")
    assert ws_html != key_html


# ── Greek content ─────────────────────────────────────────────────────────────


def test_greek_instructions_present(tmp_output):
    instance = generate_worksheet(MicroSkillId.SUBTRACTION_WITH_BORROWING, seed=0)
    assert instance.instructions_el
    # Should be in Greek (contains Greek characters)
    assert re.search(r"[α-ωΑ-Ωά-ώ]", instance.instructions_el), (
        f"Instructions do not appear to be Greek: {instance.instructions_el!r}"
    )


def test_greek_title_present(tmp_output):
    instance = generate_worksheet(MicroSkillId.DIVISION_2_5, seed=0)
    assert re.search(r"[α-ωΑ-Ωά-ώ]", instance.title_el)


# ── Worksheet types ───────────────────────────────────────────────────────────


def test_worksheet_type_stored(tmp_output):
    instance = generate_worksheet(
        MicroSkillId.MULTIPLICATION_MIXED,
        worksheet_type=WorksheetType.TIMED_FLUENCY,
        seed=0,
    )
    assert instance.worksheet_type == WorksheetType.TIMED_FLUENCY


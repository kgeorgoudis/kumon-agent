"""
Tests for app/domain/math_engine.py

Constitutional Principle II: Arithmetic Truth From Code
  Every test asserts that the Python engine produces the correct answer,
  without any LLM involvement.

Constitutional Principle I: Deterministic Before Agentic
  Given the same seed, generate_exercises() must return identical results.
"""

from __future__ import annotations

from typing import cast

import pytest

from app.domain.math_engine import generate_exercises, supported_micro_skills
from app.domain.models import MicroSkillId, Operator


# ── Reproducibility ───────────────────────────────────────────────────────────


def test_same_seed_produces_same_exercises():
    """Exercises generated with the same seed must be identical."""
    a = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=10, seed=99)
    b = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=10, seed=99)
    assert [ex.problem_text for ex in a] == [ex.problem_text for ex in b]


def test_different_seeds_produce_different_exercises():
    """Different seeds should (almost certainly) produce different exercises."""
    a = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=10, seed=1)
    b = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=10, seed=2)
    # It is theoretically possible for them to be the same by chance, but very unlikely
    assert [ex.answer for ex in a] != [ex.answer for ex in b]


# ── Count ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("count", [5, 10, 15, 20])
def test_generates_exact_count(count: int):
    exercises = generate_exercises(MicroSkillId.ADDITION_SINGLE_DIGIT, count=count, seed=0)
    assert len(exercises) == count


# ── Arithmetic correctness ────────────────────────────────────────────────────
# All arithmetic answers must be correct Python integers — never LLM output.


def test_addition_single_digit_answers_are_correct():
    exercises = generate_exercises(MicroSkillId.ADDITION_SINGLE_DIGIT, count=50, seed=7)
    for ex in exercises:
        assert ex.operator == Operator.ADD
        assert ex.answer == ex.operand_a + ex.operand_b, (
            f"Wrong answer: {ex.operand_a} + {ex.operand_b} should be "
            f"{ex.operand_a + ex.operand_b}, got {ex.answer}"
        )


def test_addition_with_carrying_always_carries():
    exercises = generate_exercises(MicroSkillId.ADDITION_WITH_CARRYING, count=100, seed=0)
    for ex in exercises:
        assert ex.answer == ex.operand_a + ex.operand_b
        # At least the units column should require a carry
        assert (int(ex.operand_a) % 10 + int(ex.operand_b) % 10) >= 10


def test_subtraction_results_non_negative():
    for skill in [
        MicroSkillId.SUBTRACTION_SINGLE_DIGIT,
        MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW,
        MicroSkillId.SUBTRACTION_WITH_BORROWING,
    ]:
        exercises = generate_exercises(skill, count=50, seed=42)
        for ex in exercises:
            assert ex.answer >= 0, f"Negative result for {ex.problem_text}"


def test_subtraction_answers_are_correct():
    exercises = generate_exercises(MicroSkillId.SUBTRACTION_WITH_BORROWING, count=50, seed=3)
    for ex in exercises:
        assert ex.answer == ex.operand_a - ex.operand_b


def test_multiplication_2_5_uses_correct_tables():
    exercises = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=100, seed=0)
    for ex in exercises:
        assert ex.operator == Operator.MULTIPLY
        assert ex.answer == ex.operand_a * ex.operand_b
        # At least one factor must be in [2, 5]
        assert ex.operand_a in range(2, 6) or ex.operand_b in range(2, 6)


def test_multiplication_6_9_uses_correct_tables():
    exercises = generate_exercises(MicroSkillId.MULTIPLICATION_6_9, count=100, seed=0)
    for ex in exercises:
        assert ex.answer == ex.operand_a * ex.operand_b
        assert ex.operand_a in range(6, 10) or ex.operand_b in range(6, 10)


def test_division_results_are_whole_numbers():
    for skill in [MicroSkillId.DIVISION_2_5, MicroSkillId.DIVISION_6_9, MicroSkillId.DIVISION_MIXED]:
        exercises = generate_exercises(skill, count=50, seed=0)
        for ex in exercises:
            assert ex.answer == int(ex.answer), f"Non-integer division result: {ex.answer}"
            assert ex.operand_a == ex.answer * ex.operand_b


def test_half_and_double_answers_correct():
    exercises = generate_exercises(MicroSkillId.HALF_AND_DOUBLE, count=50, seed=5)
    for ex in exercises:
        if ex.operator == Operator.MULTIPLY:
            assert ex.answer == ex.operand_a * ex.operand_b
        else:
            assert ex.answer == ex.operand_a // ex.operand_b


def test_ordering_numbers_exercises_have_distinct_values_and_direction():
    exercises = generate_exercises(MicroSkillId.ORDERING_NUMBERS, count=30, seed=17)
    for ex in exercises:
        assert ex.micro_skill_id == MicroSkillId.ORDERING_NUMBERS
        assert ex.prompt_numbers is not None
        assert 4 <= len(ex.prompt_numbers) <= 6
        assert len(set(ex.prompt_numbers)) == len(ex.prompt_numbers)
        assert all(1 <= n <= 1000 for n in ex.prompt_numbers)
        assert ex.ordering_direction in {"ascending", "descending"}
        assert ex.canonical_answer is not None


def test_ordering_numbers_canonical_answer_matches_direction():
    exercises = generate_exercises(MicroSkillId.ORDERING_NUMBERS, count=20, seed=23)
    for ex in exercises:
        assert ex.prompt_numbers is not None
        assert ex.canonical_answer is not None
        tokens = [int(t) for t in ex.canonical_answer.split()]
        if ex.ordering_direction == "ascending":
            assert tokens == sorted(ex.prompt_numbers)
        else:
            assert tokens == sorted(ex.prompt_numbers, reverse=True)


# ── Display text ──────────────────────────────────────────────────────────────


def test_problem_text_contains_blank():
    exercises = generate_exercises(MicroSkillId.MULTIPLICATION_MIXED, count=10, seed=0)
    for ex in exercises:
        assert "___" in ex.problem_text


def test_answer_text_does_not_contain_blank():
    exercises = generate_exercises(MicroSkillId.MULTIPLICATION_MIXED, count=10, seed=0)
    for ex in exercises:
        assert "___" not in ex.answer_text


# ── Registry completeness ─────────────────────────────────────────────────────


def test_all_supported_skills_generate_exercises():
    """Every skill registered in supported_micro_skills() must produce exercises."""
    for skill in supported_micro_skills():
        exercises = generate_exercises(skill, count=5, seed=0)
        assert len(exercises) == 5, f"Failed to generate exercises for {skill.value}"


def test_unsupported_skill_raises():
    with pytest.raises(ValueError, match="No exercise generator"):
        generate_exercises(cast(MicroSkillId, "unsupported_skill"))


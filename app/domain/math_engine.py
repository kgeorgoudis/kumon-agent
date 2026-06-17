"""
Deterministic arithmetic problem generator.

Constitutional Principle II — Arithmetic Truth From Code
---------------------------------------------------------
Every exercise answer is computed by Python code in this module.
The LLM is never consulted for any numeric result.

Constitutional Principle I — Deterministic Before Agentic
----------------------------------------------------------
Given the same micro_skill_id, count, and seed, this module always produces
exactly the same list of exercises.  This enables:
  - Reproducible worksheet regeneration
  - Deterministic test fixtures
  - Audit trail verification

Usage
-----
  from app.domain.math_engine import generate_exercises
  from app.domain.models import MicroSkillId

  exercises = generate_exercises(MicroSkillId.MULTIPLICATION_2_5, count=15, seed=42)
"""

from __future__ import annotations

import random
from typing import Callable

from app.domain.models import Exercise, MicroSkillId, Operator


# ── Internal helpers ──────────────────────────────────────────────────────────


def _exercise(
    a: int | float,
    b: int | float,
    op: Operator,
    answer: int | float,
    micro_skill_id: MicroSkillId,
) -> Exercise:
    """Build an Exercise with consistent Greek-friendly problem text."""
    blank = "___"
    problem = f"{a} {op.value} {b} = {blank}"
    answer_str = f"{a} {op.value} {b} = {answer}"
    return Exercise(
        operand_a=a,
        operand_b=b,
        operator=op,
        answer=answer,
        problem_text=problem,
        answer_text=answer_str,
        micro_skill_id=micro_skill_id,
    )


# ── Per-micro-skill generators ────────────────────────────────────────────────
# Each generator is a function: (rng: random.Random) -> Exercise


def _gen_addition_single_digit(rng: random.Random) -> Exercise:
    a = rng.randint(1, 9)
    b = rng.randint(1, 9)
    return _exercise(a, b, Operator.ADD, a + b, MicroSkillId.ADDITION_SINGLE_DIGIT)


def _gen_addition_two_digit_no_carry(rng: random.Random) -> Exercise:
    """Generate a + b where both are two-digit and no carrying is needed."""
    while True:
        a = rng.randint(10, 89)
        b = rng.randint(10, 89)
        # Check no carrying: units digits sum < 10 AND tens digits sum < 10
        if (a % 10 + b % 10) < 10 and (a // 10 + b // 10) < 10:
            return _exercise(a, b, Operator.ADD, a + b, MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY)


def _gen_addition_with_carrying(rng: random.Random) -> Exercise:
    """Generate a + b (two- or three-digit) that requires at least one carry."""
    while True:
        a = rng.randint(15, 99)
        b = rng.randint(15, 99)
        if (a % 10 + b % 10) >= 10:  # carrying in units column
            return _exercise(a, b, Operator.ADD, a + b, MicroSkillId.ADDITION_WITH_CARRYING)


def _gen_addition_three_numbers(rng: random.Random) -> Exercise:
    """Three-number addition — returns as a chained problem (a + b + c)."""
    a = rng.randint(1, 30)
    b = rng.randint(1, 30)
    c = rng.randint(1, 30)
    total = a + b + c
    blank = "___"
    problem = f"{a} + {b} + {c} = {blank}"
    answer_str = f"{a} + {b} + {c} = {total}"
    return Exercise(
        operand_a=a,
        operand_b=b,
        operator=Operator.ADD,
        answer=total,
        problem_text=problem,
        answer_text=answer_str,
        micro_skill_id=MicroSkillId.ADDITION_THREE_NUMBERS,
    )


def _gen_subtraction_single_digit(rng: random.Random) -> Exercise:
    b = rng.randint(1, 9)
    a = rng.randint(b, 9)  # ensure non-negative result
    return _exercise(a, b, Operator.SUBTRACT, a - b, MicroSkillId.SUBTRACTION_SINGLE_DIGIT)


def _gen_subtraction_two_digit_no_borrow(rng: random.Random) -> Exercise:
    while True:
        a = rng.randint(20, 99)
        b = rng.randint(10, a - 10)
        # No borrowing: units of a >= units of b AND tens of a >= tens of b
        if (a % 10) >= (b % 10) and (a // 10) >= (b // 10):
            return _exercise(a, b, Operator.SUBTRACT, a - b, MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW)


def _gen_subtraction_with_borrowing(rng: random.Random) -> Exercise:
    while True:
        a = rng.randint(20, 99)
        b = rng.randint(11, a - 1)
        if (a % 10) < (b % 10):  # borrowing needed in units column
            return _exercise(a, b, Operator.SUBTRACT, a - b, MicroSkillId.SUBTRACTION_WITH_BORROWING)


def _gen_multiplication_2_5(rng: random.Random) -> Exercise:
    table = rng.randint(2, 5)
    multiplier = rng.randint(1, 10)
    # Occasionally flip so the table factor isn't always first
    if rng.random() > 0.5:
        a, b = multiplier, table
    else:
        a, b = table, multiplier
    return _exercise(a, b, Operator.MULTIPLY, a * b, MicroSkillId.MULTIPLICATION_2_5)


def _gen_multiplication_6_9(rng: random.Random) -> Exercise:
    table = rng.randint(6, 9)
    multiplier = rng.randint(1, 10)
    if rng.random() > 0.5:
        a, b = multiplier, table
    else:
        a, b = table, multiplier
    return _exercise(a, b, Operator.MULTIPLY, a * b, MicroSkillId.MULTIPLICATION_6_9)


def _gen_multiplication_mixed(rng: random.Random) -> Exercise:
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    return _exercise(a, b, Operator.MULTIPLY, a * b, MicroSkillId.MULTIPLICATION_MIXED)


def _gen_division_2_5(rng: random.Random) -> Exercise:
    divisor = rng.randint(2, 5)
    quotient = rng.randint(1, 10)
    dividend = divisor * quotient
    return _exercise(dividend, divisor, Operator.DIVIDE, quotient, MicroSkillId.DIVISION_2_5)


def _gen_division_6_9(rng: random.Random) -> Exercise:
    divisor = rng.randint(6, 9)
    quotient = rng.randint(1, 9)
    dividend = divisor * quotient
    return _exercise(dividend, divisor, Operator.DIVIDE, quotient, MicroSkillId.DIVISION_6_9)


def _gen_division_mixed(rng: random.Random) -> Exercise:
    divisor = rng.randint(2, 9)
    quotient = rng.randint(1, 9)
    dividend = divisor * quotient
    return _exercise(dividend, divisor, Operator.DIVIDE, quotient, MicroSkillId.DIVISION_MIXED)


def _gen_half_and_double(rng: random.Random) -> Exercise:
    """Alternate between 'half of n' and 'double n'."""
    if rng.random() > 0.5:
        # double
        a = rng.randint(1, 50)
        return _exercise(a, 2, Operator.MULTIPLY, a * 2, MicroSkillId.HALF_AND_DOUBLE)
    else:
        # half — pick an even number
        a = rng.choice(range(2, 101, 2))
        return _exercise(a, 2, Operator.DIVIDE, a // 2, MicroSkillId.HALF_AND_DOUBLE)


# ── Registry ──────────────────────────────────────────────────────────────────

_GENERATORS: dict[MicroSkillId, Callable[[random.Random], Exercise]] = {
    MicroSkillId.ADDITION_SINGLE_DIGIT: _gen_addition_single_digit,
    MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY: _gen_addition_two_digit_no_carry,
    MicroSkillId.ADDITION_WITH_CARRYING: _gen_addition_with_carrying,
    MicroSkillId.ADDITION_THREE_NUMBERS: _gen_addition_three_numbers,
    MicroSkillId.SUBTRACTION_SINGLE_DIGIT: _gen_subtraction_single_digit,
    MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW: _gen_subtraction_two_digit_no_borrow,
    MicroSkillId.SUBTRACTION_WITH_BORROWING: _gen_subtraction_with_borrowing,
    MicroSkillId.MULTIPLICATION_2_5: _gen_multiplication_2_5,
    MicroSkillId.MULTIPLICATION_6_9: _gen_multiplication_6_9,
    MicroSkillId.MULTIPLICATION_MIXED: _gen_multiplication_mixed,
    MicroSkillId.DIVISION_2_5: _gen_division_2_5,
    MicroSkillId.DIVISION_6_9: _gen_division_6_9,
    MicroSkillId.DIVISION_MIXED: _gen_division_mixed,
    MicroSkillId.HALF_AND_DOUBLE: _gen_half_and_double,
}


# ── Public API ────────────────────────────────────────────────────────────────


def generate_exercises(
    micro_skill_id: MicroSkillId,
    count: int = 15,
    seed: int | None = None,
) -> list[Exercise]:
    """
    Generate a deterministic list of exercises for the given micro-skill.

    Parameters
    ----------
    micro_skill_id:
        Which micro-skill to target.
    count:
        Number of exercises to generate.
    seed:
        Random seed for reproducibility.  If None, a random seed is used and
        recorded in the returned WorksheetInstance so the sheet can be regenerated.

    Returns
    -------
    list[Exercise]
        All answers are computed by Python — never by the LLM.

    Raises
    ------
    ValueError
        If no generator is registered for the given micro_skill_id.
    """
    if micro_skill_id not in _GENERATORS:
        supported = ", ".join(k.value for k in _GENERATORS)
        raise ValueError(
            f"No exercise generator for micro-skill '{micro_skill_id.value}'. "
            f"Supported: {supported}"
        )

    rng = random.Random(seed)
    generator = _GENERATORS[micro_skill_id]
    return [generator(rng) for _ in range(count)]


def supported_micro_skills() -> list[MicroSkillId]:
    """Return the list of micro-skills that have exercise generators."""
    return list(_GENERATORS.keys())


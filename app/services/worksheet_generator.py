"""
Worksheet generator service.

Responsibilities
----------------
1. Accept a micro-skill, optional child profile, and configuration.
2. Delegate exercise generation to math_engine (deterministic).
3. Build a WorksheetInstance domain object.
4. Render HTML for both the worksheet and the answer key using Jinja2.
5. Write HTML files to the output directory.
6. Return the WorksheetInstance (with html_path / answer_key_path populated).

This service is intentionally I/O-aware (it writes files) but framework-agnostic:
it does not import FastAPI or Typer.  Both the CLI and web routes call this same
function.  Constitutional Principle IX — Shared Domain Logic.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import app.config as cfg
from app.domain.math_engine import generate_exercises
from app.domain.knowledge_base import KumonKnowledgeBase
from app.domain.models import (
    ChildProfile,
    MicroSkillId,
    WorksheetInstance,
    WorksheetType,
)

# ── Jinja2 environment ────────────────────────────────────────────────────────

_jinja_env = Environment(
    loader=FileSystemLoader(str(cfg.TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


# ── Greek display strings ─────────────────────────────────────────────────────
# Constitutional Principle VII: child-facing content in Greek.

_TITLE_EL: dict[MicroSkillId, str] = {
    MicroSkillId.ADDITION_SINGLE_DIGIT: "Πρόσθεση Μονοψήφιων",
    MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY: "Πρόσθεση Διψήφιων",
    MicroSkillId.ADDITION_WITH_CARRYING: "Πρόσθεση με Κρατούμενο",
    MicroSkillId.ADDITION_THREE_NUMBERS: "Πρόσθεση Τριών Αριθμών",
    MicroSkillId.SUBTRACTION_SINGLE_DIGIT: "Αφαίρεση Μονοψήφιων",
    MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW: "Αφαίρεση Διψήφιων",
    MicroSkillId.SUBTRACTION_WITH_BORROWING: "Αφαίρεση με Δανεισμό",
    MicroSkillId.MULTIPLICATION_2_5: "Πολλαπλασιασμός (Πίνακες 2–5)",
    MicroSkillId.MULTIPLICATION_6_9: "Πολλαπλασιασμός (Πίνακες 6–9)",
    MicroSkillId.MULTIPLICATION_MIXED: "Πολλαπλασιασμός (Μεικτοί Πίνακες)",
    MicroSkillId.DIVISION_2_5: "Διαίρεση (Διαιρέτες 2–5)",
    MicroSkillId.DIVISION_6_9: "Διαίρεση (Διαιρέτες 6–9)",
    MicroSkillId.DIVISION_MIXED: "Διαίρεση (Μεικτοί Διαιρέτες)",
    MicroSkillId.HALF_AND_DOUBLE: "Μισό και Διπλό",
    MicroSkillId.ORDERING_NUMBERS: "Διάταξη Αριθμών",
}

_INSTRUCTIONS_EL: dict[MicroSkillId, str] = {
    MicroSkillId.ADDITION_SINGLE_DIGIT: "Κάνε τις παρακάτω προσθέσεις.",
    MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY: "Κάνε τις παρακάτω προσθέσεις.",
    MicroSkillId.ADDITION_WITH_CARRYING: "Κάνε τις παρακάτω προσθέσεις. Μη ξεχάσεις το κρατούμενο!",
    MicroSkillId.ADDITION_THREE_NUMBERS: "Κάνε τις παρακάτω προσθέσεις τριών αριθμών.",
    MicroSkillId.SUBTRACTION_SINGLE_DIGIT: "Κάνε τις παρακάτω αφαιρέσεις.",
    MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW: "Κάνε τις παρακάτω αφαιρέσεις.",
    MicroSkillId.SUBTRACTION_WITH_BORROWING: "Κάνε τις παρακάτω αφαιρέσεις. Πρόσεξε τον δανεισμό!",
    MicroSkillId.MULTIPLICATION_2_5: "Κάνε τις παρακάτω πολλαπλασιασμούς.",
    MicroSkillId.MULTIPLICATION_6_9: "Κάνε τις παρακάτω πολλαπλασιασμούς.",
    MicroSkillId.MULTIPLICATION_MIXED: "Κάνε τις παρακάτω πολλαπλασιασμούς.",
    MicroSkillId.DIVISION_2_5: "Κάνε τις παρακάτω διαιρέσεις.",
    MicroSkillId.DIVISION_6_9: "Κάνε τις παρακάτω διαιρέσεις.",
    MicroSkillId.DIVISION_MIXED: "Κάνε τις παρακάτω διαιρέσεις.",
    MicroSkillId.HALF_AND_DOUBLE: "Βρες το μισό ή το διπλό κάθε αριθμού.",
    MicroSkillId.ORDERING_NUMBERS: "Διάταξε τους αριθμούς από το μικρότερο στο μεγαλύτερο.",
}


# ── Columns layout ────────────────────────────────────────────────────────────

def _columns_for_count(count: int) -> int:
    """Pick a sensible column count for the exercise grid."""
    if count <= 6:
        return 2
    if count <= 12:
        return 3
    return 4 if count >= 20 else 3


# ── Service function ──────────────────────────────────────────────────────────


def generate_worksheet(
    micro_skill_id: MicroSkillId,
    child: ChildProfile | None = None,
    count: int | None = None,
    worksheet_type: WorksheetType = WorksheetType.DRILL,
    seed: int | None = None,
) -> WorksheetInstance:
    """
    Generate a worksheet and its answer key, write HTML files, and return
    the fully-populated WorksheetInstance.

    Parameters
    ----------
    micro_skill_id:
        The micro-skill to practice.
    child:
        Optional child profile; used for display name and locale.
    count:
        Number of exercises.  Defaults to child.preferred_sheet_length or
        cfg.DEFAULT_EXERCISE_COUNT.
    worksheet_type:
        Drill, mixed review, etc.
    seed:
        Random seed for reproducibility.  Auto-generated if None.

    Returns
    -------
    WorksheetInstance
        With html_path and answer_key_path set to the written files.
    """
    # Resolve count
    if count is None:
        count = child.preferred_sheet_length if child else cfg.DEFAULT_EXERCISE_COUNT

    # Generate a random seed if not provided (stored for reproducibility)
    if seed is None:
        seed = random.randint(0, 2**31)

    # Generate exercises — pure Python, no LLM
    exercises = generate_exercises(micro_skill_id, count=count, seed=seed)

    # Fetch display strings
    title_el = _TITLE_EL.get(micro_skill_id, micro_skill_id.value.replace("_", " ").title())
    instructions_el = _INSTRUCTIONS_EL.get(micro_skill_id, "Λύσε τις παρακάτω ασκήσεις.")

    # Look up micro-skill metadata for enriched display
    meta = KumonKnowledgeBase.get_micro_skill(micro_skill_id)

    # Build domain object
    instance = WorksheetInstance(
        child_id=child.child_id if child else None,
        micro_skill_id=micro_skill_id,
        worksheet_type=worksheet_type,
        exercises=exercises,
        title_el=title_el,
        instructions_el=instructions_el,
        seed=seed,
    )

    # Build output directory: output/worksheets/YYYY-MM-DD/
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir: Path = cfg.WORKSHEETS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    child_name = child.display_name if child else cfg.DEFAULT_CHILD_NAME
    columns = _columns_for_count(count)

    # Render and write worksheet HTML
    worksheet_template = _jinja_env.get_template("worksheet.html.j2")
    worksheet_html = worksheet_template.render(
        title=title_el,
        child_name=child_name,
        instructions=instructions_el,
        exercises=exercises,
        columns=columns,
        instance_id=instance.instance_id,
        micro_skill_meta=meta,
        is_answer_key=False,
    )
    ws_path = out_dir / f"{instance.instance_id}_worksheet.html"
    ws_path.write_text(worksheet_html, encoding="utf-8")

    # Render and write answer key HTML
    key_template = _jinja_env.get_template("answer_key.html.j2")
    key_html = key_template.render(
        title=title_el,
        child_name=child_name,
        instructions=instructions_el,
        exercises=exercises,
        columns=columns,
        instance_id=instance.instance_id,
        micro_skill_meta=meta,
        is_answer_key=True,
    )
    key_path = out_dir / f"{instance.instance_id}_answer_key.html"
    key_path.write_text(key_html, encoding="utf-8")

    # Attach paths to instance
    instance = instance.model_copy(
        update={
            "html_path": str(ws_path),
            "answer_key_path": str(key_path),
        }
    )

    return instance


"""
Kumon Method Knowledge Base — embedded in-app documentation.

Constitutional Principle X: Because the operator (parent) is not a Kumon expert
or teacher, the application MUST embed contextual documentation about the Kumon
method, micro-skill definitions, progression rationale, and worksheet types.
This module is the single source of truth for that documentation and is
accessible from both the CLI (`kumon explain ...`) and the future web UI help
pages.

All method descriptions are written in plain language suitable for a parent
with no specialised teaching background.

References
----------
- Kumon Institute of Education: https://www.kumon.com/about-kumon/kumon-method/
- The content here is an original summary for educational guidance purposes,
  not a verbatim reproduction of Kumon materials.
"""

from __future__ import annotations

from app.domain.models import MicroSkillId, MicroSkillMeta, SkillId

# ── Method overview ──────────────────────────────────────────────────────────

METHOD_OVERVIEW_EN = """
THE KUMON METHOD — A PARENT'S GUIDE
====================================

What is Kumon?
--------------
Kumon is a self-learning method developed in Japan in the 1950s by Toru Kumon,
a high-school mathematics teacher whose son was struggling at school. The core
insight was simple: if exercises are carefully ordered from easy to hard, a child
can advance through the material largely on their own, building confidence with
every small win.

Key ideas
---------
1. Small steps  — each new exercise is only slightly harder than the last.
   A child who finds today's sheet too easy or too hard is on the wrong level.

2. Repetition builds fluency — the same type of problem is practised many times
   until it becomes automatic.  Fluency frees working memory for harder thinking.

3. Daily practice — short sessions every day outperform long, infrequent ones.
   Aim for 15–30 minutes, 5–7 days per week.

4. Correct before moving on — a child must reach high accuracy (≥ 90 %) before
   advancing.  Getting 60 % right and moving forward just builds shaky
   foundations.

5. Speed matters — but only after accuracy is reliable.  Timed sheets are
   introduced gradually, after the child demonstrates consistent correctness.

6. Self-correction — in classroom Kumon, children check their own work using
   answer keys.  This builds responsibility.  In this app the parent reviews
   the answer key after the child finishes.

What this app does
------------------
This app implements the Kumon loop locally:
  generate worksheet → print → child solves on paper → parent enters answers
  (kumon submit) → app scores → app suggests next sheet

The LLM (AI) is used only for optional tasks: explaining mistakes in Greek and
summarising results for the parent.
All scoring and progression decisions are made by deterministic code — you can
inspect every rule.
"""

METHOD_OVERVIEW_EL = """
Η ΜΈΘΟΔΟΣ KUMON — ΟΔΗΓΌΣ ΓΙΑ ΓΟΝΕΊΣ
======================================

Τι είναι η μέθοδος Kumon;
--------------------------
Η μέθοδος Kumon αναπτύχθηκε στην Ιαπωνία τη δεκαετία του 1950 από τον Toru
Kumon, καθηγητή μαθηματικών, του οποίου ο γιος δυσκολευόταν στο σχολείο. Η
βασική ιδέα είναι απλή: αν οι ασκήσεις διαταχθούν προσεκτικά από εύκολες
σε δύσκολες, το παιδί μπορεί να προχωρά κυρίως μόνο του, χτίζοντας αυτοπεποίθηση
με κάθε μικρή επιτυχία.

Βασικές αρχές
-------------
1. Μικρά βήματα — κάθε νέα άσκηση είναι λίγο μόνο πιο δύσκολη από την
   προηγούμενη.

2. Η επανάληψη δημιουργεί ευχέρεια — το ίδιο είδος άσκησης εξασκείται πολλές
   φορές μέχρι να γίνει αυτόματο.

3. Καθημερινή εξάσκηση — λίγα λεπτά κάθε μέρα αποδίδουν περισσότερο από
   σπάνιες μεγάλες συνεδρίες.

4. Πρώτα η ακρίβεια, μετά η ταχύτητα — το παιδί προχωρά μόνο αφού φτάσει
   υψηλή ακρίβεια (≥ 90 %).

5. Αυτοδιόρθωση — το παιδί ελέγχει τις απαντήσεις του με το κλειδί απαντήσεων
   (στη συνέχεια ο γονιός).
"""

# ── Progression guide ────────────────────────────────────────────────────────

PROGRESSION_GUIDE_EN = """
PROGRESSION RULES
=================

How the app decides what comes next
------------------------------------
Every progression decision is made by deterministic code, not by the AI.
You can always inspect the reason and override the decision.

Rules (defaults — all configurable):
  ADVANCE  : accuracy ≥ 90 % across the last 3 worksheets on the same skill
  STAY     : accuracy between 70 % and 90 %  (more practice at same level)
  STEP BACK: accuracy < 70 %, or the same mistake appears 3+ times in a row

What "accuracy" means
---------------------
  (number of correct answers) ÷ (total exercises) × 100

Speed (timing)
--------------
Timed worksheets are only introduced after accuracy is consistently ≥ 90 %.
The default target time is 2 minutes for 15 exercises, but this is configurable
per child profile.

Parent override
---------------
You can always override the suggested next worksheet.  Every override is recorded
in the audit trail so you can review the history later.  Use:
  kumon override --next <micro-skill>
or click "Override" in the web dashboard.
"""

# ── Worksheet type guide ─────────────────────────────────────────────────────

WORKSHEET_TYPE_GUIDE_EN = """
WORKSHEET TYPES
===============

DRILL
  Pure practice of one micro-skill.  All exercises target the same skill type.
  Used when introducing a new skill or building fluency.
  Example: 15 multiplication exercises, all from the 6–9 times tables.

MIXED REVIEW
  Combines the target skill (80 %) with review of a recently mastered skill
  (20 %).  Prevents forgetting.

CORRECTION SHEET
  Generated after a worksheet with low accuracy.  Focuses on the specific
  problem types that were answered incorrectly, plus scaffolded easier versions
  to rebuild confidence.

TIMED FLUENCY
  Same as DRILL but with a time target printed at the top.  Used only after
  the child reaches ≥ 90 % accuracy on the DRILL variant.

CONCEPT REINFORCEMENT
  Includes worked examples and a smaller number of exercises.  Used when the
  error pattern suggests a conceptual misunderstanding rather than careless
  mistakes.
"""

# ── Micro-skill catalogue ────────────────────────────────────────────────────

MICRO_SKILL_CATALOGUE: list[MicroSkillMeta] = [
    # ── Number sense ─────────────────────────────────────────────────────────
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.HALF_AND_DOUBLE,
        parent_skill_id=SkillId.NUMBER_SENSE,
        name_en="Half and Double",
        name_el="Μισό και Διπλό",
        description_en=(
            "Finding half of a number (÷ 2) and doubling a number (× 2). "
            "A foundational skill that prepares for multiplication and division."
        ),
        description_el=(
            "Εύρεση του μισού ενός αριθμού (÷ 2) και διπλασιασμός (× 2). "
            "Βασική δεξιότητα που προετοιμάζει για πολλαπλασιασμό και διαίρεση."
        ),
        difficulty_level=1,
        prerequisites=[],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.ORDERING_NUMBERS,
        parent_skill_id=SkillId.NUMBER_SENSE,
        name_en="Ordering Numbers",
        name_el="Διάταξη Αριθμών",
        description_en="Placing numbers in ascending or descending order up to 1000.",
        description_el="Διάταξη αριθμών σε αύξουσα ή φθίνουσα σειρά έως 1000.",
        difficulty_level=2,
        prerequisites=[],
    ),
    # ── Addition ──────────────────────────────────────────────────────────────
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.ADDITION_SINGLE_DIGIT,
        parent_skill_id=SkillId.ADDITION,
        name_en="Addition — Single Digit",
        name_el="Πρόσθεση — Μονοψήφια",
        description_en=(
            "Adding two single-digit numbers (1–9). No carrying required. "
            "The starting point for all addition work."
        ),
        description_el=(
            "Πρόσθεση δύο μονοψήφιων αριθμών (1–9). Χωρίς κρατούμενο. "
            "Αφετηρία για κάθε πρόσθεση."
        ),
        difficulty_level=1,
        prerequisites=[],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY,
        parent_skill_id=SkillId.ADDITION,
        name_en="Addition — Two Digit (no carrying)",
        name_el="Πρόσθεση — Διψήφια (χωρίς κρατούμενο)",
        description_en="Adding two two-digit numbers where no carrying is needed.",
        description_el="Πρόσθεση δύο διψήφιων αριθμών χωρίς κρατούμενο.",
        difficulty_level=2,
        prerequisites=[MicroSkillId.ADDITION_SINGLE_DIGIT],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.ADDITION_WITH_CARRYING,
        parent_skill_id=SkillId.ADDITION,
        name_en="Addition — With Carrying",
        name_el="Πρόσθεση — Με Κρατούμενο",
        description_en=(
            "Adding two- and three-digit numbers that require carrying "
            "(regrouping) of tens and hundreds."
        ),
        description_el=(
            "Πρόσθεση διψήφιων και τριψήφιων αριθμών με κρατούμενο "
            "(μεταφορά δεκάδων ή εκατοντάδων)."
        ),
        difficulty_level=3,
        prerequisites=[MicroSkillId.ADDITION_TWO_DIGIT_NO_CARRY],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.ADDITION_THREE_NUMBERS,
        parent_skill_id=SkillId.ADDITION,
        name_en="Addition — Three Numbers",
        name_el="Πρόσθεση — Τριών Αριθμών",
        description_en="Adding three numbers in a single expression.",
        description_el="Πρόσθεση τριών αριθμών σε μία έκφραση.",
        difficulty_level=4,
        prerequisites=[MicroSkillId.ADDITION_WITH_CARRYING],
    ),
    # ── Subtraction ──────────────────────────────────────────────────────────
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.SUBTRACTION_SINGLE_DIGIT,
        parent_skill_id=SkillId.SUBTRACTION,
        name_en="Subtraction — Single Digit",
        name_el="Αφαίρεση — Μονοψήφια",
        description_en="Subtracting single-digit numbers; result is always non-negative.",
        description_el="Αφαίρεση μονοψήφιων αριθμών· το αποτέλεσμα είναι πάντα ≥ 0.",
        difficulty_level=1,
        prerequisites=[MicroSkillId.ADDITION_SINGLE_DIGIT],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW,
        parent_skill_id=SkillId.SUBTRACTION,
        name_en="Subtraction — Two Digit (no borrowing)",
        name_el="Αφαίρεση — Διψήφια (χωρίς δανεισμό)",
        description_en="Subtracting two-digit numbers without borrowing.",
        description_el="Αφαίρεση διψήφιων αριθμών χωρίς δανεισμό.",
        difficulty_level=2,
        prerequisites=[MicroSkillId.SUBTRACTION_SINGLE_DIGIT],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.SUBTRACTION_WITH_BORROWING,
        parent_skill_id=SkillId.SUBTRACTION,
        name_en="Subtraction — With Borrowing",
        name_el="Αφαίρεση — Με Δανεισμό",
        description_en=(
            "Subtracting numbers that require borrowing (regrouping). "
            "A key milestone — many children find this the first genuinely hard step."
        ),
        description_el=(
            "Αφαίρεση αριθμών που απαιτεί δανεισμό. "
            "Σημαντικό ορόσημο — πολλά παιδιά το βρίσκουν πρώτη δυσκολία."
        ),
        difficulty_level=3,
        prerequisites=[MicroSkillId.SUBTRACTION_TWO_DIGIT_NO_BORROW],
    ),
    # ── Multiplication ───────────────────────────────────────────────────────
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.MULTIPLICATION_2_5,
        parent_skill_id=SkillId.MULTIPLICATION,
        name_en="Multiplication — Tables 2 to 5",
        name_el="Πολλαπλασιασμός — Πίνακες 2 έως 5",
        description_en=(
            "Multiplication facts for the 2, 3, 4, and 5 times tables (up to ×10). "
            "These are the easier tables; mastery here builds confidence for 6–9."
        ),
        description_el=(
            "Πίνακες πολλαπλασιασμού 2, 3, 4 και 5 (έως ×10). "
            "Αυτοί είναι οι πιο εύκολοι· η εκμάθησή τους δίνει αυτοπεποίθηση για 6–9."
        ),
        difficulty_level=4,
        prerequisites=[MicroSkillId.ADDITION_WITH_CARRYING, MicroSkillId.HALF_AND_DOUBLE],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.MULTIPLICATION_6_9,
        parent_skill_id=SkillId.MULTIPLICATION,
        name_en="Multiplication — Tables 6 to 9",
        name_el="Πολλαπλασιασμός — Πίνακες 6 έως 9",
        description_en=(
            "Multiplication facts for the 6, 7, 8, and 9 times tables. "
            "Typically the hardest tables to memorise — requires solid prior practice."
        ),
        description_el=(
            "Πίνακες πολλαπλασιασμού 6, 7, 8 και 9. "
            "Συνήθως οι πιο δύσκολοι — απαιτούν σταθερή εκμάθηση των προηγούμενων."
        ),
        difficulty_level=6,
        prerequisites=[MicroSkillId.MULTIPLICATION_2_5],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.MULTIPLICATION_MIXED,
        parent_skill_id=SkillId.MULTIPLICATION,
        name_en="Multiplication — Mixed Tables (2–9)",
        name_el="Πολλαπλασιασμός — Μεικτοί Πίνακες (2–9)",
        description_en="Random multiplication facts drawn from all tables 2–9.",
        description_el="Τυχαίες πράξεις πολλαπλασιασμού από όλους τους πίνακες 2–9.",
        difficulty_level=7,
        prerequisites=[MicroSkillId.MULTIPLICATION_6_9],
    ),
    # ── Division ─────────────────────────────────────────────────────────────
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.DIVISION_2_5,
        parent_skill_id=SkillId.DIVISION,
        name_en="Division — Divisors 2 to 5",
        name_el="Διαίρεση — Διαιρέτες 2 έως 5",
        description_en=(
            "Exact division by 2, 3, 4, or 5, with whole-number results. "
            "Taught as the inverse of multiplication (e.g., if 4×3=12 then 12÷4=3)."
        ),
        description_el=(
            "Ακριβής διαίρεση με 2, 3, 4 ή 5, αποτέλεσμα ακέραιος. "
            "Διδάσκεται ως αντίστροφη πράξη πολλαπλασιασμού."
        ),
        difficulty_level=5,
        prerequisites=[MicroSkillId.MULTIPLICATION_2_5],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.DIVISION_6_9,
        parent_skill_id=SkillId.DIVISION,
        name_en="Division — Divisors 6 to 9",
        name_el="Διαίρεση — Διαιρέτες 6 έως 9",
        description_en="Exact division by 6, 7, 8, or 9, with whole-number results.",
        description_el="Ακριβής διαίρεση με 6, 7, 8 ή 9, αποτέλεσμα ακέραιος.",
        difficulty_level=7,
        prerequisites=[MicroSkillId.DIVISION_2_5, MicroSkillId.MULTIPLICATION_6_9],
    ),
    MicroSkillMeta(
        micro_skill_id=MicroSkillId.DIVISION_MIXED,
        parent_skill_id=SkillId.DIVISION,
        name_en="Division — Mixed Divisors (2–9)",
        name_el="Διαίρεση — Μεικτοί Διαιρέτες (2–9)",
        description_en="Exact division by any divisor from 2 to 9.",
        description_el="Ακριβής διαίρεση με οποιονδήποτε διαιρέτη από 2 έως 9.",
        difficulty_level=8,
        prerequisites=[MicroSkillId.DIVISION_6_9],
    ),
]

# Build a lookup dict for fast access by MicroSkillId
MICRO_SKILL_BY_ID: dict[MicroSkillId, MicroSkillMeta] = {
    m.micro_skill_id: m for m in MICRO_SKILL_CATALOGUE
}


# ── Public API ────────────────────────────────────────────────────────────────


class KumonKnowledgeBase:
    """
    Embedded documentation about the Kumon method.

    Constitutional Principle X: In-App Documentation.

    Every public method returns a plain string suitable for display in the
    CLI (via Rich) or in a web help page.  Methods are intentionally simple
    so future callers can easily swap in Markdown rendering.
    """

    @staticmethod
    def get_method_overview(lang: str = "en") -> str:
        if lang.startswith("el"):
            return METHOD_OVERVIEW_EL
        return METHOD_OVERVIEW_EN

    @staticmethod
    def get_progression_guide(lang: str = "en") -> str:
        return PROGRESSION_GUIDE_EN

    @staticmethod
    def get_worksheet_type_guide(lang: str = "en") -> str:
        return WORKSHEET_TYPE_GUIDE_EN

    @staticmethod
    def get_micro_skill(micro_skill_id: MicroSkillId) -> MicroSkillMeta | None:
        return MICRO_SKILL_BY_ID.get(micro_skill_id)

    @staticmethod
    def get_all_micro_skills() -> list[MicroSkillMeta]:
        return list(MICRO_SKILL_CATALOGUE)

    @staticmethod
    def get_micro_skills_for_skill(skill_id: SkillId) -> list[MicroSkillMeta]:
        return [m for m in MICRO_SKILL_CATALOGUE if m.parent_skill_id == skill_id]

    @staticmethod
    def get_skill_description(skill_id: SkillId, lang: str = "en") -> str:
        skills = KumonKnowledgeBase.get_micro_skills_for_skill(skill_id)
        if not skills:
            return f"No micro-skills defined for {skill_id.value}."
        lines = [f"Skill: {skill_id.value.replace('_', ' ').title()}", ""]
        for ms in sorted(skills, key=lambda s: s.difficulty_level):
            desc = ms.description_el if lang.startswith("el") else ms.description_en
            name = ms.name_el if lang.startswith("el") else ms.name_en
            lines.append(f"  Level {ms.difficulty_level}: {name}")
            lines.append(f"    {desc}")
            lines.append("")
        return "\n".join(lines)


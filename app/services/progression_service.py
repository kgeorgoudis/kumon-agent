"""Deterministic progression decision service."""

from __future__ import annotations

from statistics import mean

from app.domain.knowledge_base import KumonKnowledgeBase
from app.domain.models import MicroSkillId, ProgressDecision
from app.persistence.database import Database, default_db


def _catalogue_order() -> list[MicroSkillId]:
    return [m.micro_skill_id for m in KumonKnowledgeBase.get_all_micro_skills()]


def _next_skill(micro_skill_id: MicroSkillId) -> MicroSkillId:
    ordered = _catalogue_order()
    idx = ordered.index(micro_skill_id)
    return ordered[idx + 1] if idx < len(ordered) - 1 else micro_skill_id


def _previous_skill(micro_skill_id: MicroSkillId) -> MicroSkillId:
    ordered = _catalogue_order()
    idx = ordered.index(micro_skill_id)
    return ordered[idx - 1] if idx > 0 else micro_skill_id


def evaluate_progression(
    child_id: str,
    micro_skill_id: MicroSkillId,
    db: Database = default_db,
    persist: bool = True,
) -> ProgressDecision:
    """Evaluate deterministic progression from recent worksheet accuracy."""
    points = db.list_progress_points(child_id=child_id, limit=50)
    relevant = [p for p in points if p.micro_skill_id == micro_skill_id.value][:3]

    if not relevant:
        decision = ProgressDecision(
            child_id=child_id,
            from_micro_skill_id=micro_skill_id,
            next_micro_skill_id=micro_skill_id,
            action="stay",
            reason="No scored worksheets yet for this micro-skill.",
            reason_el="Δεν υπάρχουν ακόμη βαθμολογημένα φύλλα για αυτή τη δεξιότητα.",
            accuracy_pct=0.0,
        )
    else:
        accuracy = float(mean(p.accuracy_pct for p in relevant))
        if len(relevant) < 3:
            action = "stay"
            next_skill = micro_skill_id
            reason = "Insufficient history (need 3 worksheets) to change level."
            reason_el = "Χρειάζονται 3 φύλλα για αλλαγή επιπέδου."
        elif accuracy >= 90.0:
            action = "advance"
            next_skill = _next_skill(micro_skill_id)
            reason = "Recent accuracy is >= 90% across 3 worksheets."
            reason_el = "Η πρόσφατη ακρίβεια είναι >= 90% στα τελευταία 3 φύλλα."
        elif accuracy < 70.0:
            action = "step_back"
            next_skill = _previous_skill(micro_skill_id)
            reason = "Recent accuracy is below 70% across 3 worksheets."
            reason_el = "Η πρόσφατη ακρίβεια είναι κάτω από 70% στα τελευταία 3 φύλλα."
        else:
            action = "stay"
            next_skill = micro_skill_id
            reason = "Recent accuracy is between 70% and 90%; keep practicing."
            reason_el = "Η πρόσφατη ακρίβεια είναι μεταξύ 70% και 90%· συνεχίζουμε εξάσκηση."

        decision = ProgressDecision(
            child_id=child_id,
            from_micro_skill_id=micro_skill_id,
            next_micro_skill_id=next_skill,
            action=action,
            reason=reason,
            reason_el=reason_el,
            accuracy_pct=accuracy,
        )

    if persist:
        db.save_progress_decision(decision)
    return decision


"""Worksheet review facade built on top of tutor graph orchestration."""

from __future__ import annotations

from app.agents.agent_graph import create_task, run_tutor_graph
from app.agents.state import TutorTaskType
from app.agents.tools import build_manual_review_context
from app.domain.models import TutorOutcome
from app.persistence.database import Database, default_db


def review_confirmed_worksheet(
    instance_id: str,
    *,
    include_narrative: bool = True,
    db: Database = default_db,
) -> TutorOutcome:
    """Review a confirmed scored worksheet using grounded deterministic context."""
    context = build_manual_review_context(instance_id=instance_id, db=db)
    task = create_task(TutorTaskType.WORKSHEET_REVIEW)
    outcome = run_tutor_graph(
        {
            "task": task,
            "deterministic_context": context,
            "request_narrative": include_narrative,
        },
        db=db,
    )
    if not include_narrative:
        outcome.summary_el = "Δεν ζητήθηκε ανασκόπηση LLM. Εμφανίζονται μόνο τα ντετερμινιστικά δεδομένα."
    return outcome


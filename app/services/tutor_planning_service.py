"""Next-step planning facade built on top of tutor graph orchestration."""

from __future__ import annotations

from app.agents.agent_graph import create_task, run_tutor_graph
from app.agents.state import TutorTaskType
from app.agents.tools import build_next_step_plan_context
from app.domain.models import ChildProfile, TutorOutcome
from app.persistence.database import Database, default_db


def plan_next_step(
    child: ChildProfile,
    *,
    limit: int = 20,
    include_narrative: bool = True,
    db: Database = default_db,
) -> TutorOutcome:
    """Generate grounded next-step worksheet suggestions for one child."""
    context = build_next_step_plan_context(child=child, limit=limit, db=db)
    task = create_task(TutorTaskType.NEXT_STEP_PLANNING, child_id=child.child_id)
    outcome = run_tutor_graph(
        {
            "task": task,
            "deterministic_context": context,
            "request_narrative": include_narrative,
        },
        db=db,
    )
    return outcome


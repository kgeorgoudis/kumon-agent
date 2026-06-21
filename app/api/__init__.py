"""
FastAPI routes.

All handlers delegate to app/services/ (Constitutional Principle IX).
Keep this module thin; no domain logic lives here.

Constitutional alignment:
  - IX. Shared Domain Logic: Service layer remains the single source of truth
  - V. Paper Workflow First: API is secondary to CLI, which is secondary to paper loop
"""

from fastapi import FastAPI
from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import app.config as cfg
from app.persistence.database import default_db
from app.services.progress_summary_service import build_progress_report
from app.web.progress_view import report_context

api = FastAPI(
    title="Kumon Agent API",
    description="Local-first math tutoring API.",
    version="0.1.0",
)

templates = Jinja2Templates(directory=str(cfg.TEMPLATES_DIR))


def _resolve_child_profile(child_name: str | None):
    if child_name:
        for profile in default_db.list_child_profiles():
            if profile.display_name.lower() == child_name.lower():
                return profile
        return None

    profile = default_db.get_child_profile(cfg.DEFAULT_CHILD_ID)
    if profile:
        return profile
    profiles = default_db.list_child_profiles()
    return profiles[0] if profiles else None


@api.get("/health")
def health() -> dict:
    return {"status": "ok"}


@api.get("/progress", response_class=HTMLResponse)
def progress_page(
    request: Request,
    child: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    llm: bool = Query(default=True),
):
    profile = _resolve_child_profile(child)
    if profile is None:
        # Soft empty state for unknown/missing child profile.
        from app.domain.models import ChildProfile

        profile = ChildProfile(
            child_id="unknown",
            display_name=child or "Άγνωστο παιδί",
            age=cfg.DEFAULT_CHILD_AGE,
            grade_level=cfg.DEFAULT_CHILD_GRADE,
        )

    report = build_progress_report(
        child=profile,
        limit=limit,
        include_narrative=llm,
        db=default_db,
    )
    context = report_context(report)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="progress_summary.html.j2",
        context=context,
    )

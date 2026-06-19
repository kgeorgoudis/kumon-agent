"""
FastAPI routes — stub for Milestone 2+.

All handlers delegate to app/services/ (Constitutional Principle IX).
Keep this module thin; no domain logic lives here.

Constitutional alignment:
  - IX. Shared Domain Logic: Service layer remains the single source of truth
  - V. Paper Workflow First: API is secondary to CLI, which is secondary to paper loop
"""

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import app.config as cfg
from app.persistence.database import default_db
from app.services.ingestion_service import IngestionError, ingest_submission
from app.services.progress_summary_service import build_progress_report
from app.services.ocr_review_service import (
    OcrFieldNotFoundError,
    OcrResultNotFoundError,
    approve_ocr_result,
    correct_ocr_field,
    list_ocr_fields,
)
from app.services.scoring_service import RescoreError, rescore_ocr_result
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


@api.post("/ocr/ingest")
def ocr_ingest(file_path: str, worksheet: str, engine: str = "tesseract", threshold: float = cfg.OCR_CONFIDENCE_THRESHOLD) -> dict:
    try:
        outcome = ingest_submission(
            file_path=file_path,
            instance_id=worksheet,
            engine=engine,
            threshold=threshold,
            db=default_db,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail={"code": getattr(exc, "code", "ERR_OCR_FAILED"), "message": str(exc)})
    return outcome.__dict__


@api.get("/ocr/{ocr_result_id}/fields")
def ocr_fields(ocr_result_id: str) -> dict:
    try:
        fields = list_ocr_fields(ocr_result_id, db=default_db)
    except OcrResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "ERR_OCR_RESULT_NOT_FOUND", "message": str(exc)})
    return {"ocr_result_id": ocr_result_id, "fields": [f.model_dump(mode="json") for f in fields]}


@api.post("/ocr/{ocr_result_id}/correct")
def ocr_correct(ocr_result_id: str, exercise_id: str, value: str) -> dict:
    try:
        correct_ocr_field(ocr_result_id, exercise_id, value, db=default_db)
    except OcrResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "ERR_OCR_RESULT_NOT_FOUND", "message": str(exc)})
    except OcrFieldNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "ERR_OCR_FIELD_NOT_FOUND", "message": str(exc)})
    return {"status": "ok", "ocr_result_id": ocr_result_id, "exercise_id": exercise_id}


@api.post("/ocr/{ocr_result_id}/approve")
def ocr_approve(ocr_result_id: str) -> dict:
    try:
        approve_ocr_result(ocr_result_id, db=default_db)
    except OcrResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "ERR_OCR_RESULT_NOT_FOUND", "message": str(exc)})
    return {"status": "reviewed", "ocr_result_id": ocr_result_id}


@api.post("/ocr/{ocr_result_id}/rescore")
def ocr_rescore(ocr_result_id: str) -> dict:
    try:
        snapshot = rescore_ocr_result(ocr_result_id, db=default_db)
    except RescoreError as exc:
        raise HTTPException(status_code=400, detail={"code": getattr(exc, "code", "ERR_REVIEW_NOT_COMPLETE"), "message": str(exc)})
    return snapshot.model_dump(mode="json")


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



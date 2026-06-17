"""OCR ingestion service.

This module handles artifact intake and OCR processing orchestration.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import mimetypes
import re
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
import pytesseract
import pypdfium2 as pdfium

from app import config as cfg
from app.agents.llm_client import classify_ocr_fallback_exception, get_ocr_fallback_client
from app.domain.models import OcrField, OcrResult, OcrResultStatus, SubmissionStatus, WorksheetSubmission
from app.domain.ocr_mapping import ExtractedToken, detect_slot_mismatch, map_tokens_to_slots
from app.persistence.database import Database, default_db


class IngestionError(RuntimeError):
    """Base exception for ingestion failures."""


class FileNotFoundIngestionError(IngestionError):
    code = "ERR_FILE_NOT_FOUND"


class UnsupportedFormatIngestionError(IngestionError):
    code = "ERR_UNSUPPORTED_FORMAT"


class WorksheetNotFoundIngestionError(IngestionError):
    code = "ERR_WORKSHEET_NOT_FOUND"


class OcrProcessingError(IngestionError):
    code = "ERR_OCR_FAILED"


class OcrMismatchedError(IngestionError):
    code = "ERR_OCR_MISMATCHED"


ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".pdf"}


@dataclass(frozen=True)
class IngestedArtifact:
    source_path: Path
    stored_path: Path
    file_hash: str


@dataclass(frozen=True)
class IngestionOutcome:
    submission_id: str
    ocr_result_id: str
    instance_id: str
    fields_total: int
    fields_needing_review: int
    status: str


def validate_upload_path(file_path: str) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundIngestionError(f"File not found: {file_path}")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise UnsupportedFormatIngestionError(f"Unsupported file format: {path.suffix}")
    return path


def detect_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def store_submission_artifact(path: Path) -> IngestedArtifact:
    cfg.SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    file_hash = compute_file_hash(path)
    target_name = f"{file_hash}{path.suffix.lower()}"
    target_path = cfg.SUBMISSIONS_DIR / target_name
    if not target_path.exists():
        shutil.copy2(path, target_path)
    return IngestedArtifact(source_path=path, stored_path=target_path, file_hash=file_hash)


def run_local_ocr(file_path: Path, expected_count: int | None = None) -> tuple[list[str], list[float]]:
    """Run local OCR and return extracted tokens + confidences.

    For PDFs, conversion support is intentionally deferred. This function raises
    a clear error so the caller can mark submission as failed.
    """
    if file_path.suffix.lower() == ".pdf":
        return _run_pdf_ocr(file_path, expected_count=expected_count)

    try:
        with Image.open(file_path) as image:
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
    except Exception as exc:
        raise OcrProcessingError(f"OCR execution failed: {exc}") from exc

    tokens, confidences = _extract_answers_from_ocr_data(data, expected_count=expected_count)

    if not tokens:
        raise OcrProcessingError("OCR produced zero readable tokens.")

    return tokens, confidences


def run_hybrid_ocr(
    file_path: Path,
    *,
    expected_count: int,
    confidence_threshold: float,
    engine: str,
) -> tuple[list[str], list[float]]:
    """Run deterministic OCR first, then optional local vision fallback for low-confidence slots."""
    tokens, confidences = run_local_ocr(file_path, expected_count=None)
    if engine == "tesseract":
        return tokens, confidences

    mismatch_detected = len(tokens) != expected_count
    low_indices = [idx for idx, conf in enumerate(confidences) if conf < confidence_threshold]
    if (not low_indices and not mismatch_detected) or not cfg.OCR_FALLBACK_ENABLED:
        return tokens, confidences

    try:
        vision_result = run_local_vision_fallback(
            file_path=file_path,
            slot_indices=low_indices,
            existing_tokens=tokens,
            expected_count=expected_count,
        )
    except Exception as exc:  # graceful degrade is required by the spec
        reason, status_code, message = classify_ocr_fallback_exception(exc)
        prefix = "OCR fallback unavailable, continuing with deterministic OCR-only mode"
        if reason == "memory_ceiling":
            prefix = "OCR fallback model could not be loaded because it exceeds the local memory ceiling; continuing with deterministic OCR-only mode"
        elif reason == "auth_error":
            prefix = "OCR fallback authentication failed; continuing with deterministic OCR-only mode"
        elif reason == "model_not_found":
            prefix = "OCR fallback model is not available on the local server; continuing with deterministic OCR-only mode"
        status = f" (status {status_code})" if status_code is not None else ""
        warnings.warn(f"{prefix}{status}: {message}")
        return tokens, confidences

    if vision_result is None:
        return tokens, confidences

    vision_tokens, vision_confidences = vision_result
    if mismatch_detected:
        return vision_tokens, vision_confidences

    for idx in low_indices:
        if 0 <= idx < len(tokens) and idx < len(vision_tokens):
            replacement = vision_tokens[idx].strip()
            if replacement:
                tokens[idx] = replacement
                confidences[idx] = vision_confidences[idx]
    return tokens, confidences


def run_local_vision_fallback(
    *,
    file_path: Path,
    slot_indices: list[int],
    existing_tokens: list[str],
    expected_count: int,
) -> tuple[list[str], list[float]] | None:
    """Ask the local vision model for ordered worksheet answers.

    Returns `(answers, confidences)` when the model provides exactly
    `expected_count` ordered answers. Otherwise returns `None` so ingestion can
    gracefully continue with deterministic OCR-only results.
    """
    client = get_ocr_fallback_client()
    data_url = _build_fallback_data_url(file_path)
    prompt = _build_vision_fallback_prompt(
        expected_count=expected_count,
        slot_indices=slot_indices,
        existing_tokens=existing_tokens,
    )
    response = client.chat.completions.create(
        model=cfg.OCR_FALLBACK_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise OCR assistant for children's handwritten math worksheets. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        return None
    parsed = _parse_vision_fallback_response(content)
    if parsed is None:
        return None
    answers, confidences = parsed
    if len(answers) != expected_count or len(confidences) != expected_count:
        return None
    return answers, confidences


def _build_fallback_data_url(file_path: Path) -> str:
    mime_type = detect_mime_type(file_path)
    if file_path.suffix.lower() == ".pdf":
        image = _render_pdf_first_page(file_path)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        payload = buffer.getvalue()
        mime_type = "image/png"
    else:
        payload = file_path.read_bytes()
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _render_pdf_first_page(file_path: Path) -> Image.Image:
    try:
        pdf = pdfium.PdfDocument(str(file_path))
    except Exception as exc:
        raise OcrProcessingError(f"Unable to open PDF for vision fallback: {exc}") from exc
    try:
        if len(pdf) == 0:
            raise OcrProcessingError("PDF has no pages.")
        page = pdf[0]
        bitmap = page.render(scale=2.0)
        return bitmap.to_pil()
    finally:
        try:
            pdf.close()
        except Exception:
            pass


def _build_vision_fallback_prompt(*, expected_count: int, slot_indices: list[int], existing_tokens: list[str]) -> str:
    current_values = {idx: existing_tokens[idx] for idx in range(len(existing_tokens))}
    return (
        f"This worksheet has exactly {expected_count} answer slots in top-to-bottom order. "
        f"Tesseract OCR currently extracted these values by slot index: {json.dumps(current_values, ensure_ascii=False)}. "
        f"Please inspect the worksheet image and return strict JSON with this schema: "
        '{"answers":["..."],"confidences":[0.0]}. '
        f"The answers array must contain exactly {expected_count} strings, one per slot in order. "
        f"Focus especially on these uncertain slot indices: {slot_indices}. "
        "Use an empty string for unreadable answers. Confidence values must be between 0 and 1. "
        "Return JSON only, with no markdown fences."
    )


def _parse_vision_fallback_response(content: str) -> tuple[list[str], list[float]] | None:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    answers_raw = payload.get("answers")
    confidences_raw = payload.get("confidences")
    if not isinstance(answers_raw, list):
        return None
    answers = [_normalize_answer_candidate(str(item)) for item in answers_raw]
    if not isinstance(confidences_raw, list) or len(confidences_raw) != len(answers):
        confidences = [0.81 if answer else 0.0 for answer in answers]
    else:
        confidences = []
        for item in confidences_raw:
            try:
                confidences.append(max(0.0, min(1.0, float(item))))
            except (TypeError, ValueError):
                confidences.append(0.0)
    return answers, confidences


def _run_pdf_ocr(file_path: Path, expected_count: int | None = None) -> tuple[list[str], list[float]]:
    """OCR a single-page PDF by rendering page 1 to an image first."""
    try:
        pdf = pdfium.PdfDocument(str(file_path))
    except Exception as exc:
        raise OcrProcessingError(f"Unable to open PDF: {exc}") from exc

    try:
        page_count = len(pdf)
        if page_count == 0:
            raise OcrProcessingError("PDF has no pages.")
        if page_count > 1:
            raise OcrProcessingError("Only single-page PDF is supported in this phase.")

        page = pdf[0]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
        data = pytesseract.image_to_data(
            pil_image,
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
        )
    except OcrProcessingError:
        raise
    except Exception as exc:
        raise OcrProcessingError(f"PDF OCR execution failed: {exc}") from exc
    finally:
        try:
            pdf.close()
        except Exception:
            pass

    tokens, confidences = _extract_answers_from_ocr_data(data, expected_count=expected_count)

    if not tokens:
        raise OcrProcessingError("OCR produced zero readable tokens.")

    return tokens, confidences


def _normalize_answer_candidate(text: str) -> str:
    """Normalize OCR token into a likely numeric answer format."""
    value = text.strip()
    substitutions = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        ",": ".",
    }
    for src, target in substitutions.items():
        value = value.replace(src, target)
    value = re.sub(r"[^0-9\-.]", "", value)
    return value


def _extract_answers_from_ocr_data(data: dict, expected_count: int | None = None) -> tuple[list[str], list[float]]:
    """Extract likely answer tokens line-by-line, preferring values after '='.

    This dramatically improves worksheet OCR quality compared to taking the first N
    tokens from the whole page.
    """
    words: list[dict] = []
    raw_text = data.get("text", [])
    raw_conf = data.get("conf", [])
    left = data.get("left", [])
    top = data.get("top", [])
    block = data.get("block_num", [])
    par = data.get("par_num", [])
    line = data.get("line_num", [])

    total = len(raw_text)
    for i in range(total):
        txt = (raw_text[i] or "").strip()
        if not txt:
            continue
        try:
            conf = max(0.0, min(1.0, float(raw_conf[i]) / 100.0))
        except Exception:
            conf = 0.0
        words.append(
            {
                "text": txt,
                "conf": conf,
                "left": int(left[i]) if i < len(left) else 0,
                "top": int(top[i]) if i < len(top) else 0,
                "line_key": (
                    int(block[i]) if i < len(block) else 0,
                    int(par[i]) if i < len(par) else 0,
                    int(line[i]) if i < len(line) else 0,
                ),
            }
        )

    if not words:
        return [], []

    grouped: dict[tuple[int, int, int], list[dict]] = {}
    for w in words:
        grouped.setdefault(w["line_key"], []).append(w)

    line_candidates: list[tuple[int, int, str, float]] = []
    for row in grouped.values():
        row_sorted = sorted(row, key=lambda w: w["left"])
        texts = [w["text"] for w in row_sorted]
        row_text = " ".join(texts)

        # Keep likely exercise rows first (worksheet rows always include '=')
        is_exercise_row = "=" in row_text

        eq_idx = -1
        for idx, t in enumerate(texts):
            if "=" in t:
                eq_idx = idx
                break

        search_segment = row_sorted[eq_idx + 1 :] if eq_idx >= 0 else row_sorted
        candidate = None
        for w in reversed(search_segment):
            normalized = _normalize_answer_candidate(w["text"])
            if normalized not in {"", "-", ".", "-."}:
                candidate = (normalized, float(w["conf"]))
                break

        if candidate is None:
            # If nothing found after '=', keep explicit blank to avoid slot shifting.
            conf_avg = sum(w["conf"] for w in row_sorted) / len(row_sorted)
            candidate = ("", conf_avg)

        top_min = min(w["top"] for w in row_sorted)
        left_min = min(w["left"] for w in row_sorted)
        # Sort key starts with exercise-row priority (0=exercise row, 1=other row).
        line_candidates.append((0 if is_exercise_row else 1, top_min, left_min, candidate[0], candidate[1]))

    line_candidates.sort(key=lambda x: (x[0], x[1], x[2]))

    # Prefer exercise rows; preserve blanks to keep slot alignment deterministic.
    tokens = [c[3] for c in line_candidates]
    confidences = [c[4] for c in line_candidates]

    if expected_count is not None:
        if len(tokens) >= expected_count:
            tokens = tokens[:expected_count]
            confidences = confidences[:expected_count]
        else:
            missing = expected_count - len(tokens)
            tokens.extend([""] * missing)
            confidences.extend([0.0] * missing)

    # Fallback to generic token extraction if line-based extraction under-fills.
    if expected_count is not None and all(t == "" for t in tokens):
        generic_tokens: list[str] = []
        generic_conf: list[float] = []
        for w in sorted(words, key=lambda item: (item["top"], item["left"])):
            normalized = _normalize_answer_candidate(w["text"])
            if normalized in {"", "-", ".", "-."}:
                continue
            generic_tokens.append(normalized)
            generic_conf.append(float(w["conf"]))
        if generic_tokens:
            if len(generic_tokens) >= expected_count:
                tokens = generic_tokens[:expected_count]
                confidences = generic_conf[:expected_count]
            else:
                tokens = generic_tokens + [""] * (expected_count - len(generic_tokens))
                confidences = generic_conf + [0.0] * (expected_count - len(generic_conf))

    return tokens, confidences


def ingest_submission(
    file_path: str,
    instance_id: str,
    engine: str = "hybrid",
    threshold: float | None = None,
    db: Database | None = None,
) -> IngestionOutcome:
    """Ingest a worksheet artifact and persist OCR extraction results."""
    db = db or default_db
    confidence_threshold = threshold if threshold is not None else cfg.OCR_CONFIDENCE_THRESHOLD

    source_path = validate_upload_path(file_path)
    worksheet = db.get_worksheet_instance(instance_id)
    if worksheet is None:
        raise WorksheetNotFoundIngestionError(f"Worksheet not found: {instance_id}")

    artifact = store_submission_artifact(source_path)
    mime_type = detect_mime_type(source_path)

    submission = WorksheetSubmission(
        instance_id=instance_id,
        child_id=worksheet.child_id,
        file_path=str(artifact.stored_path),
        mime_type=mime_type,
        file_hash=artifact.file_hash,
    )
    db.save_worksheet_submission(submission)

    failed_result: OcrResult | None = None
    try:
        token_texts, token_confidences = run_hybrid_ocr(
            source_path,
            expected_count=len(worksheet.exercises),
            confidence_threshold=confidence_threshold,
            engine=engine,
        )
    except Exception as exc:
        failed_result = OcrResult(
            submission_id=submission.submission_id,
            instance_id=instance_id,
            engine=engine,
            engine_version=str(getattr(pytesseract, "__version__", "unknown")),
            fallback_model=cfg.OCR_FALLBACK_MODEL if cfg.OCR_FALLBACK_ENABLED else None,
            confidence_threshold=confidence_threshold,
            overall_confidence=0.0,
            status=OcrResultStatus.FAILED,
        )
        db.save_ocr_result(failed_result)
        db.update_submission_status(
            submission.submission_id,
            status=SubmissionStatus.FAILED,
            failure_reason=str(exc),
        )
        if isinstance(exc, IngestionError):
            raise
        raise OcrProcessingError(str(exc)) from exc

    raw_tokens = [
        ExtractedToken(text=text, confidence=token_confidences[idx] if idx < len(token_confidences) else 0.0)
        for idx, text in enumerate(token_texts)
    ]
    is_mismatched = detect_slot_mismatch(raw_tokens, expected_count=len(worksheet.exercises))
    mapped = map_tokens_to_slots(raw_tokens, expected_count=len(worksheet.exercises))

    overall_conf = sum((t.confidence for t in mapped), 0.0) / len(mapped) if mapped else 0.0
    ocr_result = OcrResult(
        submission_id=submission.submission_id,
        instance_id=instance_id,
        engine=engine,
        engine_version=str(getattr(pytesseract, "__version__", "unknown")),
        fallback_model=cfg.OCR_FALLBACK_MODEL if cfg.OCR_FALLBACK_ENABLED else None,
        confidence_threshold=confidence_threshold,
        overall_confidence=overall_conf,
        status=OcrResultStatus.INGESTED,
    )
    db.save_ocr_result(ocr_result)
    db.transition_ocr_result_status(ocr_result.ocr_result_id, OcrResultStatus.EXTRACTED)

    fields: list[OcrField] = []
    for idx, exercise in enumerate(worksheet.exercises):
        token = mapped[idx]
        needs_review = token.confidence < confidence_threshold or token.text == ""
        fields.append(
            OcrField(
                ocr_result_id=ocr_result.ocr_result_id,
                exercise_id=exercise.exercise_id,
                slot_index=idx,
                raw_value=token.text,
                confidence=token.confidence,
                needs_review=needs_review,
                original_ocr_value=token.text,
            )
        )

    db.save_ocr_fields(fields)
    db.update_submission_status(submission.submission_id, status=SubmissionStatus.OCR_PROCESSED)

    needs_review_count = sum(1 for f in fields if f.needs_review)
    if is_mismatched:
        db.transition_ocr_result_status(ocr_result.ocr_result_id, OcrResultStatus.MISMATCHED)
        final_status = OcrResultStatus.MISMATCHED
    else:
        db.transition_ocr_result_status(ocr_result.ocr_result_id, OcrResultStatus.NEEDS_REVIEW)
        final_status = OcrResultStatus.NEEDS_REVIEW

    return IngestionOutcome(
        submission_id=submission.submission_id,
        ocr_result_id=ocr_result.ocr_result_id,
        instance_id=instance_id,
        fields_total=len(fields),
        fields_needing_review=needs_review_count,
        status=final_status.value,
    )


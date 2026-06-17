"""
Local LLM client — OpenAI-compatible endpoint.

Constitutional Principle VIII — Local-First Architecture:
  The LLM runs at http://127.0.0.1:8000/v1 (configurable via KUMON_LLM_BASE_URL).
  No data leaves the local machine unless the operator explicitly points
  KUMON_LLM_BASE_URL at a remote service.

Constitutional Principle I — Deterministic Before Agentic:
  This client is used ONLY for tasks that genuinely benefit from language
  understanding: explanations, summaries, and OCR disambiguation.
  It is NEVER used for arithmetic evaluation or progression decisions.

Usage (future milestones)
-------------------------
  from app.agents.llm_client import get_llm_client
  client = get_llm_client()
  response = client.chat.completions.create(
      model=cfg.LLM_MODEL,
      messages=[{"role": "user", "content": "..."}],
  )

LangGraph graphs are defined as separate modules in app/agents/ and imported
by the services that need them.  The client is a shared singleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

import app.config as cfg


_ONE_PIXEL_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9QhKQAAAAASUVORK5CYII="
)


@dataclass(frozen=True)
class OcrFallbackProbeResult:
    ok: bool
    stage: str
    reason: str
    message: str
    status_code: int | None
    configured_model: str
    available_models: list[str]


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """
    Return a cached OpenAI client pointed at the local LLM endpoint.

    The first call initialises the client; subsequent calls return the same
    instance.  Thread-safe for read-only use.
    """
    return OpenAI(
        base_url=cfg.LLM_BASE_URL,
        api_key=cfg.LLM_API_KEY,
        timeout=cfg.LLM_TIMEOUT,
    )


@lru_cache(maxsize=1)
def get_ocr_fallback_client() -> OpenAI:
    """Return a cached client for the local vision OCR fallback endpoint."""
    return OpenAI(
        base_url=cfg.OCR_FALLBACK_BASE_URL,
        api_key=cfg.OCR_FALLBACK_API_KEY,
        timeout=cfg.OCR_FALLBACK_TIMEOUT,
    )


def classify_ocr_fallback_exception(exc: Exception) -> tuple[str, int | None, str]:
    """Classify common local vision fallback failures for actionable diagnostics."""
    status_code = getattr(exc, "status_code", None)
    message = str(exc)
    lowered = message.lower()

    if status_code == 401 or "invalid api key" in lowered or "authentication" in lowered:
        return "auth_error", status_code, message
    if status_code == 404 or "model" in lowered and "not found" in lowered:
        return "model_not_found", status_code, message
    if status_code == 507 or "memory ceiling" in lowered or "does not fit under the memory ceiling" in lowered:
        return "memory_ceiling", status_code, message
    if "image_url" in lowered or "vision" in lowered or "multimodal" in lowered:
        return "vision_request_error", status_code, message
    return "unknown_error", status_code, message


def probe_ocr_fallback() -> OcrFallbackProbeResult:
    """Probe the configured OCR fallback endpoint with model listing and a tiny vision request."""
    client = get_ocr_fallback_client()
    configured_model = cfg.OCR_FALLBACK_MODEL

    try:
        models = client.models.list()
        available_models = [getattr(model, "id", str(model)) for model in models.data]
    except Exception as exc:
        reason, status_code, message = classify_ocr_fallback_exception(exc)
        return OcrFallbackProbeResult(
            ok=False,
            stage="models.list",
            reason=reason,
            message=message,
            status_code=status_code,
            configured_model=configured_model,
            available_models=[],
        )

    try:
        response = client.chat.completions.create(
            model=configured_model,
            temperature=0,
            max_tokens=5,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Reply with exactly: ok"},
                        {"type": "image_url", "image_url": {"url": _ONE_PIXEL_PNG_DATA_URL}},
                    ],
                }
            ],
        )
    except Exception as exc:
        reason, status_code, message = classify_ocr_fallback_exception(exc)
        return OcrFallbackProbeResult(
            ok=False,
            stage="chat.completions.create",
            reason=reason,
            message=message,
            status_code=status_code,
            configured_model=configured_model,
            available_models=available_models,
        )

    content = ""
    if response.choices:
        content = response.choices[0].message.content or ""
    return OcrFallbackProbeResult(
        ok=True,
        stage="chat.completions.create",
        reason="ok",
        message=content,
        status_code=200,
        configured_model=configured_model,
        available_models=available_models,
    )


def is_llm_available() -> bool:
    """
    Quick health-check: returns True if the local LLM endpoint responds.

    Used by the CLI to warn the parent when the LLM is offline (the core
    worksheet workflow still works without it).
    """
    try:
        client = get_llm_client()
        models = client.models.list()
        return len(models.data) > 0
    except Exception:
        return False


from __future__ import annotations

from app.agents.llm_client import classify_ocr_fallback_exception


class _Exc(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def test_classify_auth_error():
    reason, status_code, message = classify_ocr_fallback_exception(
        _Exc("Invalid API key", status_code=401)
    )
    assert reason == "auth_error"
    assert status_code == 401
    assert "Invalid API key" in message


def test_classify_memory_ceiling_error():
    reason, status_code, message = classify_ocr_fallback_exception(
        _Exc("Model does not fit under the memory ceiling", status_code=507)
    )
    assert reason == "memory_ceiling"
    assert status_code == 507
    assert "memory ceiling" in message


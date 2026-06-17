"""Utilities for mapping OCR text output to worksheet answer slots.

The ingestion pipeline can use this module to normalize extracted text and align
values to known exercise slots in a generated worksheet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedToken:
    """A normalized OCR token and optional confidence."""

    text: str
    confidence: float = 0.0


def normalize_ocr_text(raw: str) -> str:
    """Normalize OCR output to a numeric-friendly value string.

    Rules:
    - Trim whitespace
    - Replace common OCR glyph confusions used in handwritten digits
    - Keep leading minus sign and decimal point
    """
    value = raw.strip()
    substitutions = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
    }
    for src, target in substitutions.items():
        value = value.replace(src, target)
    value = re.sub(r"[^0-9\-.]", "", value)
    return value


def map_tokens_to_slots(tokens: list[ExtractedToken], expected_count: int) -> list[ExtractedToken]:
    """Return exactly `expected_count` tokens by truncating or padding blanks.

    This deterministic behavior keeps ingest idempotent when OCR returns extra
    noise tokens or misses some answer slots.
    """
    normalized: list[ExtractedToken] = [
        ExtractedToken(text=normalize_ocr_text(t.text), confidence=t.confidence)
        for t in tokens
    ]

    if len(normalized) >= expected_count:
        return normalized[:expected_count]

    missing = expected_count - len(normalized)
    return normalized + [ExtractedToken(text="", confidence=0.0) for _ in range(missing)]


def detect_slot_mismatch(tokens: list[ExtractedToken], expected_count: int) -> bool:
    """Detect when OCR produced a different number of candidate tokens than expected."""
    return len(tokens) != expected_count



"""Shared test helpers for the Kumon Agent."""

from __future__ import annotations

from app.domain.models import OcrField, OcrResult, OcrResultStatus


def build_test_ocr_result(*, submission_id: str, instance_id: str, status: OcrResultStatus) -> OcrResult:
	return OcrResult(
		submission_id=submission_id,
		instance_id=instance_id,
		engine="hybrid",
		engine_version="test",
		overall_confidence=0.75,
		confidence_threshold=0.80,
		status=status,
	)


def build_test_ocr_field(*, ocr_result_id: str, exercise_id: str, slot_index: int) -> OcrField:
	return OcrField(
		ocr_result_id=ocr_result_id,
		exercise_id=exercise_id,
		slot_index=slot_index,
		raw_value="12",
		confidence=0.9,
		needs_review=False,
	)


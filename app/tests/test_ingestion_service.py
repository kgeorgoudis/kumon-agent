from __future__ import annotations

from pathlib import Path

import pytest

import app.config as cfg
from app.domain.models import MicroSkillId, OcrResultStatus, SubmissionStatus
from app.persistence.database import Database
from app.services import ingestion_service
from app.services.ingestion_service import (
    FileNotFoundIngestionError,
    UnsupportedFormatIngestionError,
    WorksheetNotFoundIngestionError,
    OcrProcessingError,
    ingest_submission,
    validate_upload_path,
)
from app.services.worksheet_generator import generate_worksheet


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture()
def tmp_paths(tmp_path: Path, monkeypatch):
    worksheets_dir = tmp_path / "worksheets"
    submissions_dir = tmp_path / "submissions"
    monkeypatch.setattr(cfg, "WORKSHEETS_DIR", worksheets_dir)
    monkeypatch.setattr(cfg, "SUBMISSIONS_DIR", submissions_dir)
    monkeypatch.setattr(cfg, "OCR_FALLBACK_ENABLED", False)
    worksheets_dir.mkdir(parents=True, exist_ok=True)
    submissions_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture()
def sample_image(tmp_paths: Path) -> Path:
    image = tmp_paths / "completed_sheet.jpg"
    image.write_bytes(b"fake-image-content")
    return image


def _prepare_worksheet(db: Database):
    ws = generate_worksheet(MicroSkillId.ADDITION_SINGLE_DIGIT, count=3, seed=7)
    db.save_worksheet_instance(ws)
    return ws


def test_validate_upload_path_missing_file_raises():
    with pytest.raises(FileNotFoundIngestionError):
        validate_upload_path("/tmp/does-not-exist.jpg")


def test_validate_upload_path_unsupported_format_raises(tmp_paths: Path):
    f = tmp_paths / "bad.txt"
    f.write_text("x")
    with pytest.raises(UnsupportedFormatIngestionError):
        validate_upload_path(str(f))


def test_ingest_requires_existing_worksheet(db: Database, sample_image: Path):
    with pytest.raises(WorksheetNotFoundIngestionError):
        ingest_submission(str(sample_image), instance_id="missing", db=db)


def test_ingest_persists_artifact_result_and_fields(
    db: Database,
    sample_image: Path,
    monkeypatch,
):
    ws = _prepare_worksheet(db)

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["12", "34", "56"], [0.95, 0.5, 0.99]),
    )

    outcome = ingest_submission(
        file_path=str(sample_image),
        instance_id=ws.instance_id,
        threshold=0.85,
        db=db,
    )

    assert outcome.fields_total == 3
    assert outcome.fields_needing_review == 1

    submission = db.get_submission(outcome.submission_id)
    assert submission is not None
    assert submission.status == SubmissionStatus.OCR_PROCESSED
    assert Path(submission.file_path).exists()

    result = db.get_ocr_result(outcome.ocr_result_id)
    assert result is not None
    fields = db.get_ocr_fields(outcome.ocr_result_id)
    assert len(fields) == 3
    assert any(f.needs_review for f in fields)


def test_ingest_handles_short_ocr_output_by_padding(
    db: Database,
    sample_image: Path,
    monkeypatch,
):
    ws = _prepare_worksheet(db)

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["77"], [0.91]),
    )

    outcome = ingest_submission(str(sample_image), instance_id=ws.instance_id, db=db)
    fields = db.get_ocr_fields(outcome.ocr_result_id)
    assert len(fields) == 3
    assert fields[0].raw_value == "77"
    assert fields[1].raw_value == ""
    assert fields[2].raw_value == ""
    assert outcome.status == OcrResultStatus.MISMATCHED.value


def test_ingest_marks_failed_when_ocr_yields_zero_tokens(
    db: Database,
    sample_image: Path,
    monkeypatch,
):
    ws = _prepare_worksheet(db)

    def _raise(_p, expected_count=None):
        raise OcrProcessingError("OCR produced zero readable tokens.")

    monkeypatch.setattr(ingestion_service, "run_local_ocr", _raise)

    with pytest.raises(OcrProcessingError):
        ingest_submission(str(sample_image), instance_id=ws.instance_id, db=db)

    with db.connect() as conn:
        row = conn.execute(
            "SELECT status FROM ocr_results ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["status"] == OcrResultStatus.FAILED.value


def test_ingest_marks_mismatched_when_token_count_differs(
    db: Database,
    sample_image: Path,
    monkeypatch,
):
    ws = _prepare_worksheet(db)

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["10", "20"], [0.91, 0.95]),
    )

    outcome = ingest_submission(str(sample_image), instance_id=ws.instance_id, db=db)
    assert outcome.status == OcrResultStatus.MISMATCHED.value


def test_ingest_pdf_ocr_path_supported(
    db: Database,
    tmp_paths: Path,
    monkeypatch,
):
    ws = _prepare_worksheet(db)
    pdf_file = tmp_paths / "completed_sheet.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["11", "22", "33"], [0.9, 0.9, 0.9]),
    )

    outcome = ingest_submission(str(pdf_file), instance_id=ws.instance_id, db=db)
    assert outcome.fields_total == 3
    submission = db.get_submission(outcome.submission_id)
    assert submission is not None
    assert submission.mime_type == "application/pdf"


def test_run_local_ocr_rejects_multi_page_pdf(monkeypatch, tmp_paths: Path):
    pdf_file = tmp_paths / "multi.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")

    class FakePdf:
        def __len__(self):
            return 2

        def close(self):
            return None

    monkeypatch.setattr(ingestion_service.pdfium, "PdfDocument", lambda *_args, **_kwargs: FakePdf())

    with pytest.raises(OcrProcessingError, match="single-page PDF"):
        ingestion_service.run_local_ocr(pdf_file)


def test_extract_answers_from_ocr_data_prefers_tokens_after_equals():
    data = {
        "text": ["1.", "7", "x", "8", "=", "56", "2.", "9", "+", "4", "=", "13"],
        "conf": ["90", "90", "90", "90", "90", "92", "90", "90", "90", "90", "90", "93"],
        "left": [5, 20, 35, 45, 60, 75, 5, 20, 35, 45, 60, 75],
        "top": [10, 10, 10, 10, 10, 10, 30, 30, 30, 30, 30, 30],
        "block_num": [1] * 12,
        "par_num": [1] * 12,
        "line_num": [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2],
    }

    tokens, conf = ingestion_service._extract_answers_from_ocr_data(data, expected_count=2)
    assert tokens[:2] == ["56", "13"]
    assert len(conf) >= 2


def test_extract_answers_preserves_blank_slots_for_alignment():
    data = {
        "text": [
            "1.", "7", "x", "8", "=", "56",
            "2.", "9", "+", "4", "=",  # blank answer row
            "3.", "3", "x", "5", "=", "15",
        ],
        "conf": ["90"] * 17,
        "left": [5, 20, 35, 45, 60, 75, 5, 20, 35, 45, 60, 5, 20, 35, 45, 60, 75],
        "top": [10, 10, 10, 10, 10, 10, 30, 30, 30, 30, 30, 50, 50, 50, 50, 50, 50],
        "block_num": [1] * 17,
        "par_num": [1] * 17,
        "line_num": [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3],
    }

    tokens, _ = ingestion_service._extract_answers_from_ocr_data(data, expected_count=3)
    assert tokens == ["56", "", "15"]


def test_extract_answers_handles_noisy_positions_from_rotated_capture():
    # Simulates low-quality capture where OCR emits noisy line groupings.
    data = {
        "text": ["2.", "9", "+", "4", "=", "13", "1.", "7", "x", "8", "=", "56"],
        "conf": ["60", "58", "62", "61", "55", "52", "70", "71", "69", "68", "70", "67"],
        "left": [15, 30, 45, 60, 75, 90, 15, 30, 45, 60, 75, 90],
        "top": [45, 45, 45, 45, 45, 45, 20, 20, 20, 20, 20, 20],
        "block_num": [1] * 12,
        "par_num": [1] * 12,
        "line_num": [5, 5, 5, 5, 5, 5, 3, 3, 3, 3, 3, 3],
    }

    tokens, conf = ingestion_service._extract_answers_from_ocr_data(data, expected_count=2)
    assert tokens == ["56", "13"]
    assert all(c >= 0.0 for c in conf[:2])


def test_run_hybrid_ocr_replaces_low_confidence_slots_with_vision_fallback(monkeypatch, tmp_paths: Path):
    image = tmp_paths / "sheet.jpg"
    image.write_bytes(b"fake-image-content")
    monkeypatch.setattr(cfg, "OCR_FALLBACK_ENABLED", True)

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["18", "3", "12"], [0.20, 0.95, 0.30]),
    )
    monkeypatch.setattr(
        ingestion_service,
        "run_local_vision_fallback",
        lambda **_kwargs: (["16", "3", "14"], [0.92, 0.95, 0.88]),
    )

    tokens, confidences = ingestion_service.run_hybrid_ocr(
        image,
        expected_count=3,
        confidence_threshold=0.80,
        engine="hybrid",
    )

    assert tokens == ["16", "3", "14"]
    assert confidences == [0.92, 0.95, 0.88]


def test_run_hybrid_ocr_uses_vision_output_when_tesseract_count_is_mismatched(monkeypatch, tmp_paths: Path):
    image = tmp_paths / "sheet.jpg"
    image.write_bytes(b"fake-image-content")
    monkeypatch.setattr(cfg, "OCR_FALLBACK_ENABLED", True)

    monkeypatch.setattr(
        ingestion_service,
        "run_local_ocr",
        lambda _p, expected_count=None: (["18", "3"], [0.20, 0.10]),
    )
    monkeypatch.setattr(
        ingestion_service,
        "run_local_vision_fallback",
        lambda **_kwargs: (["16", "7", "14"], [0.92, 0.90, 0.88]),
    )

    tokens, confidences = ingestion_service.run_hybrid_ocr(
        image,
        expected_count=3,
        confidence_threshold=0.80,
        engine="hybrid",
    )

    assert tokens == ["16", "7", "14"]
    assert confidences == [0.92, 0.90, 0.88]



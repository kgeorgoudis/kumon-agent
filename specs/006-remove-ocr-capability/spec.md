# Feature Specification: Remove OCR Capability

**Feature Branch**: `006-remove-ocr-capability`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "To clean up the code, please remove OCR capability from all files. I have decided to remove OCR and submit worksheets manually using uv run kumon submit command."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Manual Submission Workflow (Priority: P1)

The parent uses `kumon submit <instance_id>` as the sole way to record a child's answers. No OCR ingestion, no review pipeline, and no vision fallback is ever invoked. The codebase is free of OCR-related modules, dependencies, tests, and configuration.

**Why this priority**: OCR is being permanently removed. The manual submission workflow is the only supported path and must work cleanly without any OCR remnants that could confuse future developers or cause unused-dependency errors.

**Independent Test**: Run `uv run kumon submit <instance_id> --answers "1,2,3"` against a generated worksheet and verify it scores correctly. Confirm no OCR-related imports, modules, or dependencies remain.

**Acceptance Scenarios**:

1. **Given** a generated worksheet, **When** the parent runs `kumon submit <instance_id> --answers "..."`, **Then** answers are scored deterministically and a progress snapshot is saved.
2. **Given** the cleaned codebase, **When** all tests are run, **Then** no test imports or references OCR models, OCR services, or OCR configuration.
3. **Given** the cleaned codebase, **When** `pyproject.toml` is inspected, **Then** `pytesseract` and `pypdfium2` are absent.

---

### User Story 2 - No Broken Imports or Runtime Errors (Priority: P2)

After OCR removal, all remaining imports compile cleanly. No module references a deleted file. The `kumon generate` and `kumon progress` commands still work without any change to their interfaces.

**Why this priority**: Incomplete cleanup leaves dangling imports that break startup. Every command that worked before must still work after removal.

**Independent Test**: Run `uv run kumon --help` and `uv run kumon list-skills` and confirm they succeed. Run `uv run pytest` and confirm all remaining tests pass.

**Acceptance Scenarios**:

1. **Given** the cleaned codebase, **When** `uv run kumon --help` is executed, **Then** it exits successfully with no import errors.
2. **Given** the cleaned codebase, **When** `uv run pytest` is executed, **Then** all tests pass and no test references a deleted OCR module.

---

### Edge Cases

- What happens with existing SQLite databases that have rows in `ocr_results` and `ocr_fields`? The tables remain in the schema for backward compatibility but no new rows are written.
- What happens if the progress query previously fell back to OCR-path snapshots? The fallback path is removed; only manual-submission-linked snapshots are counted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST remove `app/services/ingestion_service.py` entirely.
- **FR-002**: The system MUST remove `app/services/ocr_review_service.py` entirely.
- **FR-003**: The system MUST remove `app/domain/ocr_mapping.py` entirely.
- **FR-004**: The system MUST remove all OCR-related domain models: `OcrResult`, `OcrField`, `OcrResultStatus`, `OcrValueSource`, `SubmissionStatus`, `WorksheetSubmission`, and the `_OCR_STATUS_TRANSITIONS` lifecycle dictionary.
- **FR-005**: The system MUST remove OCR-related methods from `app/persistence/database.py` while preserving existing table schemas for backward compatibility with existing SQLite databases.
- **FR-006**: The system MUST remove OCR-related routes from `app/api/__init__.py`.
- **FR-007**: The system MUST remove OCR configuration variables from `app/config.py`.
- **FR-008**: The system MUST remove `classify_ocr_fallback_exception`, `get_ocr_fallback_client`, `probe_ocr_fallback`, and `OcrFallbackProbeResult` from `app/agents/llm_client.py`.
- **FR-009**: The system MUST remove `pytesseract` and `pypdfium2` from `pyproject.toml` dependencies.
- **FR-010**: The system MUST remove `pillow` from `pyproject.toml` as it was only used by the OCR pipeline.
- **FR-011**: The system MUST delete all OCR-focused test files: `test_ingestion_service.py`, `test_ocr_review_service.py`, `test_rescoring_idempotency.py`, and `test_llm_client.py`.
- **FR-012**: The system MUST remove OCR-related assertions and imports from `test_database.py` and `app/tests/__init__.py`.
- **FR-013**: The system MUST remove the `rescore_ocr_result` function and its OCR-specific error classes from `app/services/scoring_service.py`.
- **FR-014**: The manual submission workflow (`kumon submit`) MUST continue to function identically after all OCR removals.

### Key Entities

- **ManualSubmission**: Retained. The only supported submission pathway.
- **ManualAnswerEntry**: Retained. Stores parent-entered answers.
- **ScoreResultSnapshot**: Retained but simplified — `ocr_result_id` field removed.
- **WorksheetInstance**: Retained unchanged.
- **ChildProfile**: Retained unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `uv run pytest` completes with zero failures and zero OCR-related test files present.
- **SC-002**: No Python file in `app/` imports from `pytesseract`, `pypdfium2`, `PIL`, or `app.services.ingestion_service`.
- **SC-003**: `uv run kumon submit <id> --answers "..." --no-confirm` completes successfully for any generated worksheet.
- **SC-004**: `pyproject.toml` contains no references to `pytesseract`, `pypdfium2`, or `pillow`.
- **SC-005**: `grep -r "ocr_result_id\|OcrResult\|OcrField\|ocr_review\|ingestion_service\|pytesseract" app/` returns no results except for legacy table column definitions in `database.py`.

## Assumptions

- Existing SQLite databases with OCR rows (`ocr_results`, `ocr_fields`, `worksheet_submissions`) are retained on disk but no longer written to. These tables remain in the DDL for non-destructive upgrade.
- The `openai` Python package is retained because it is still used for the LLM narrative/progress summary feature.
- The `pillow` package is removed since it was used exclusively by the OCR image-processing pipeline.
- The `python-magic` package is removed since it was not actively used after ingestion service removal.
- No users depend on the `POST /ocr/ingest`, `GET /ocr/{id}/fields`, `POST /ocr/{id}/correct`, `POST /ocr/{id}/approve`, or `POST /ocr/{id}/rescore` API endpoints.
- Historical OCR-path score snapshots (where `submission_id IS NULL`) will no longer appear in `kumon progress` output after the progress query is simplified.


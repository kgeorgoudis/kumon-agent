# Research: Remove OCR Capability

## Decision 1: Remove OCR modules entirely and keep manual submission as the only ingestion path

- Decision: Delete OCR-specific modules (`ingestion_service`, `ocr_review_service`, `ocr_mapping`) and remove OCR runtime entry points.
- Rationale: The product owner explicitly chose manual entry via `kumon submit`; keeping dormant OCR code increases maintenance surface and causes dependency drift.
- Alternatives considered:
  - Keep OCR modules behind feature flags: rejected because dead code and transitive deps still impose maintenance and import risk.
  - Keep OCR in a separate package: rejected because no current requirement for OCR and added complexity is unjustified.

## Decision 2: Preserve SQLite backward compatibility while removing OCR runtime behavior

- Decision: Keep legacy OCR tables/columns in schema and keep compatibility migration for `score_result_snapshots.ocr_result_id` nullable, but remove all OCR CRUD/service methods from active code paths.
- Rationale: Existing local databases should remain readable without destructive migration while the application transitions to manual-only runtime behavior.
- Alternatives considered:
  - Drop OCR tables immediately: rejected due to data-loss risk for existing local installs.
  - Full DB migration with table drop/rename: rejected for this cleanup because it adds operational risk and no user-facing value.

## Decision 3: Simplify progress snapshot lookup to submission-linked snapshots only

- Decision: Use `score_result_snapshots.submission_id` as the sole source for progress timeline rows.
- Rationale: OCR-path fallback snapshots (`submission_id IS NULL`) no longer have a supported producer; keeping fallback logic obscures behavior and may count stale historical artifacts.
- Alternatives considered:
  - Keep fallback indefinitely: rejected because it preserves obsolete behavior tied to removed OCR workflow.

## Decision 4: Remove OCR-only dependencies from manifest

- Decision: Remove `pytesseract`, `pypdfium2`, `pillow`, and `python-magic` from `pyproject.toml`.
- Rationale: These libraries were tied to OCR ingestion and image/PDF handling; removing them reduces install size and avoids unnecessary native/runtime requirements.
- Alternatives considered:
  - Retain dependencies for potential future OCR return: rejected because speculative retention conflicts with explicit product direction.

## Decision 5: Remove OCR API contracts and retain only active endpoints

- Decision: Remove `/ocr/*` API endpoints from `app/api/__init__.py` and document only `/health` and `/progress` as supported API contracts.
- Rationale: Public surface should match implemented behavior; stale endpoints create confusion and incorrect client expectations.
- Alternatives considered:
  - Keep stub `/ocr/*` endpoints returning errors: rejected because this preserves unsupported contract surface.


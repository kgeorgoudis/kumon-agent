# API Contract (Post-OCR Removal)

## Scope

Documents active FastAPI endpoints after removing OCR interfaces.

## Active Endpoints

### `GET /health`
- Response: `200 OK`
- Body:
```json
{"status": "ok"}
```

### `GET /progress`
- Query params:
  - `child` (optional string)
  - `limit` (optional int, default 20, range 1..200)
  - `llm` (optional bool, default true)
- Response: `200 OK` HTML page (`progress_summary.html.j2`) with deterministic progress context and optional narrative.

## Removed Endpoints

The following OCR endpoints are removed and are no longer part of the supported contract:
- `POST /ocr/ingest`
- `GET /ocr/{ocr_result_id}/fields`
- `POST /ocr/{ocr_result_id}/correct`
- `POST /ocr/{ocr_result_id}/approve`
- `POST /ocr/{ocr_result_id}/rescore`

Clients depending on these endpoints must migrate to manual submission workflows through CLI/UI.


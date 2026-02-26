## Unreleased

### Added
- **Start Ingest Date**: Calendar date-picker on both Add Account and Edit Account forms; overrides skip-older-than-days when set.
- **Background Refresh-All**: Refresh all attachments runs as a background task with live progress polling (processed/total/errors) instead of blocking the server.
- **Refresh-All Status Endpoint**: `GET /api/emails/refresh-all-attachments/status` returns real-time progress.
- **Invoice Link Extraction**: `GET /api/emails/{id}` now extracts invoice/document links from body HTML for the frontend Preview Link button.
- Playwright-based link capture: `POST /api/emails/{id}/capture-link` prints links to PDF headlessly and saves into the ingestion path with Reggie processing.
- Inline attachment/document previews via `GET /api/documents/{id}/preview` (PDF/image) in Emails and Documents pages.
- UI controls: per-email refresh files, link preview + print-to-PDF, global refresh-all attachments in Settings.

### Fixed / Improved
- **Critical**: Download-all endpoints (`/documents/email/{id}/download-all`, `/documents/download-all`) used wrong dependency (`get_db` instead of `get_settings`) — caused server crash on any download-all request.
- **Critical**: Playwright import at module level in emails router crashed the server if Playwright wasn't installed — now conditional with `HAS_PLAYWRIGHT` flag and clear error message.
- **Critical**: `get_settings()` dependency was missing entirely from documents router.
- Pipeline: invoice link downloads now guard against empty content and deduplicate by SHA-256 hash (matching attachment behavior).
- Pipeline: attachment deduplication per email by SHA in pipeline.
- Fetcher: `start_ingest_date` (ISO YYYY-MM-DD) takes priority over `skip_older_than_days` for age filtering.
- Settings routes: `start_ingest_date` included in account list response, create, and update.
- API timeout increased from 30s to 120s for long-running operations.
- Preview endpoint streams PNG bytes (no temp files).

### Dependencies
- Added Playwright (Chromium installed via `python -m playwright install chromium`).
- Tesseract OCR for image and scanned PDF text extraction.

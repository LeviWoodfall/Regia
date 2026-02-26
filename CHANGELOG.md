## Unreleased

### Added
- Playwright-based link capture: `/api/emails/{id}/capture-link` prints links to PDF headlessly and saves into the ingestion path with Reggie processing.
- Inline attachment/document previews via `/api/documents/{id}/preview` (PDF/image) in Emails and Documents pages.
- UI controls: per-email refresh files, link preview + print-to-PDF, global refresh-all attachments in Settings.

### Fixed / Improved
- Deduplicate documents per email by SHA in pipeline.
- Preview endpoint streams PNG bytes (no temp files).

### Dependencies
- Added Playwright (Chromium installed via `python -m playwright install chromium`).

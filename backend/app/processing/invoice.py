"""
Invoice link detection and download for Regia.
Securely downloads invoices/documents from links found in emails.
"""

import os
import re
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote

import httpx

logger = logging.getLogger("regia.processing.invoice")

# Max download size: 100MB
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024

# Allowed content types for download
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/octet-stream",
}

# Request timeout in seconds
DOWNLOAD_TIMEOUT = 60


async def download_invoice_from_link(url: str) -> Optional[Dict[str, Any]]:
    """
    Download a document from a URL.
    Returns dict with filename, content, content_type, or None on failure.
    Only downloads PDF files for security.
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https"):
            logger.warning(f"Refusing to download from non-HTTP URL: {url}")
            return None

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=DOWNLOAD_TIMEOUT,
            max_redirects=5,
        ) as client:
            # HEAD request first to check content type and size
            try:
                head_resp = await client.head(url)
                content_type = head_resp.headers.get("content-type", "").split(";")[0].strip()
                content_length = int(head_resp.headers.get("content-length", 0))

                if content_length > MAX_DOWNLOAD_SIZE:
                    logger.warning(f"File too large ({content_length} bytes): {url}")
                    return None
            except Exception:
                # HEAD might not be supported, proceed with GET
                pass

            # Download the file
            response = await client.get(url)
            response.raise_for_status()

            content = response.content
            content_type = response.headers.get("content-type", "").split(";")[0].strip()

            if len(content) > MAX_DOWNLOAD_SIZE:
                logger.warning(f"Downloaded file too large ({len(content)} bytes): {url}")
                return None

            # Determine filename
            filename = _extract_filename(response, url)

            # Verify it's a PDF (either by content-type or magic bytes)
            is_pdf = (
                content_type == "application/pdf"
                or filename.lower().endswith(".pdf")
                or content[:5] == b"%PDF-"
            )

            if not is_pdf:
                logger.info(f"Skipping non-PDF download from {url} (type: {content_type})")
                return None

            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            logger.info(f"Downloaded invoice: {filename} ({len(content)} bytes) from {url}")

            return {
                "filename": filename,
                "content": content,
                "content_type": "application/pdf",
                "source_url": url,
                "size": len(content),
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading {url}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Failed to download from {url}: {e}")
        return None


def _extract_filename(response: httpx.Response, url: str) -> str:
    """Extract filename from response headers or URL."""
    # Try Content-Disposition header
    cd = response.headers.get("content-disposition", "")
    if cd:
        match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', cd)
        if match:
            filename = unquote(match.group(1).strip())
            if filename:
                return _sanitize(filename)

    # Fall back to URL path
    path = urlparse(str(response.url)).path
    filename = os.path.basename(unquote(path))
    if filename and "." in filename:
        return _sanitize(filename)

    # Generate a name
    return "downloaded_invoice.pdf"


def _sanitize(name: str) -> str:
    """Sanitize filename."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return sanitized.strip('. ') or "document"

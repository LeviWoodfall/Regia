"""
PDF processing for Regia.
Extracts text content and metadata from PDF files using PyMuPDF.
"""

import logging
from typing import Optional

logger = logging.getLogger("regia.processing.pdf")


def extract_pdf_text(filepath: str) -> str:
    """
    Extract embedded text from a PDF file.
    Returns concatenated text from all pages.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not installed - cannot extract PDF text")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract text from {filepath}: {e}")
        return ""


def get_pdf_page_count(filepath: str) -> int:
    """Get the number of pages in a PDF file."""
    try:
        import fitz
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get page count for {filepath}: {e}")
        return 0


def get_pdf_metadata(filepath: str) -> dict:
    """Extract metadata from a PDF file."""
    try:
        import fitz
        doc = fitz.open(filepath)
        metadata = doc.metadata or {}
        doc.close()
        return metadata
    except Exception as e:
        logger.error(f"Failed to get metadata for {filepath}: {e}")
        return {}


def render_pdf_page(filepath: str, page_number: int = 0, dpi: int = 150) -> Optional[bytes]:
    """
    Render a PDF page as a PNG image.
    Used for document previews in the UI.
    """
    try:
        import fitz
        doc = fitz.open(filepath)
        if page_number >= len(doc):
            doc.close()
            return None
        page = doc[page_number]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes
    except Exception as e:
        logger.error(f"Failed to render page {page_number} of {filepath}: {e}")
        return None

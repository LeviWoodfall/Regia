"""
OCR processing for Regia.
Extracts text from scanned PDFs and images using Tesseract.
"""

import logging
import tempfile
from typing import Optional

from app.config import OCRConfig

logger = logging.getLogger("regia.processing.ocr")


def ocr_pdf(filepath: str, config: OCRConfig) -> str:
    """
    Perform OCR on a PDF file to extract text from scanned pages.
    Uses PyMuPDF to render pages as images, then Tesseract for OCR.
    """
    if not config.enabled:
        return ""

    try:
        import fitz
        import pytesseract
        from PIL import Image
        import io
    except ImportError as e:
        logger.warning(f"OCR dependencies not available: {e}")
        return ""

    text_parts = []
    try:
        doc = fitz.open(filepath)
        for page_num, page in enumerate(doc):
            # Render page at configured DPI
            mat = fitz.Matrix(config.dpi / 72, config.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # OCR the rendered image
            image = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(
                image,
                lang=config.language,
            )
            if page_text.strip():
                text_parts.append(page_text)

            logger.debug(f"OCR page {page_num + 1}: {len(page_text)} chars")

        doc.close()
    except Exception as e:
        logger.error(f"OCR failed for {filepath}: {e}")

    return "\n\n".join(text_parts)


def ocr_image(filepath: str, config: OCRConfig) -> str:
    """Perform OCR on a single image file."""
    if not config.enabled:
        return ""

    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        logger.warning(f"OCR dependencies not available: {e}")
        return ""

    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image, lang=config.language)
        return text
    except Exception as e:
        logger.error(f"OCR failed for image {filepath}: {e}")
        return ""


def is_tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

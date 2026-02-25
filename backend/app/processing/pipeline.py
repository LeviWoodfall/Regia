"""
Document processing pipeline for Regia.
Orchestrates: attachment extraction → storage → hashing → OCR → LLM classification.
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import AppSettings
from app.database import Database
from app.security import hash_file
from app.email_engine.parser import ParsedEmail, Attachment
from app.processing.pdf_handler import extract_pdf_text, get_pdf_page_count
from app.processing.ocr import ocr_pdf
from app.processing.invoice import download_invoice_from_link

logger = logging.getLogger("regia.processing.pipeline")


class ProcessingPipeline:
    """
    Processes emails through the full pipeline:
    1. Extract & store attachments
    2. Compute & verify file hashes
    3. OCR text extraction
    4. LLM classification & summarization
    5. Download invoice links
    """

    def __init__(self, db: Database, settings: AppSettings):
        self.db = db
        self.settings = settings
        self._classifier = None

    def _get_classifier(self):
        """Lazy-load the LLM classifier."""
        if self._classifier is None:
            from app.llm.classifier import DocumentClassifier
            self._classifier = DocumentClassifier(self.settings.llm)
        return self._classifier

    async def process_email(self, email_id: int, parsed: ParsedEmail) -> Dict[str, Any]:
        """
        Process a single email through the full pipeline.
        Returns processing summary.
        """
        result = {
            "email_id": email_id,
            "documents_saved": 0,
            "invoices_downloaded": 0,
            "errors": [],
        }

        # Update email status
        self.db.execute(
            "UPDATE emails SET status = 'processing' WHERE id = ?", (email_id,)
        )

        try:
            # 1. Process attachments (PDFs)
            for attachment in parsed.attachments:
                if self._is_processable(attachment):
                    try:
                        doc_id = await self._process_attachment(
                            email_id, parsed, attachment
                        )
                        if doc_id:
                            result["documents_saved"] += 1
                    except Exception as e:
                        error = f"Failed to process attachment '{attachment.filename}': {e}"
                        logger.error(error)
                        result["errors"].append(error)

            # 2. Process invoice links
            if (
                self.settings.security.allow_outbound_connections
                and parsed.invoice_links
            ):
                for link in parsed.invoice_links:
                    try:
                        doc_id = await self._process_invoice_link(
                            email_id, parsed, link
                        )
                        if doc_id:
                            result["invoices_downloaded"] += 1
                    except Exception as e:
                        error = f"Failed to download invoice from '{link}': {e}"
                        logger.error(error)
                        result["errors"].append(error)

            # 3. Classify the email itself using LLM
            try:
                classifier = self._get_classifier()
                email_classification = await classifier.classify_email(
                    subject=parsed.subject,
                    sender=parsed.sender_email,
                    body_preview=parsed.body_text[:500],
                )
                email_summary = await classifier.summarize_text(
                    parsed.body_text[:2000]
                )
                self.db.execute(
                    "UPDATE emails SET classification = ?, llm_summary = ? WHERE id = ?",
                    (email_classification, email_summary, email_id),
                )
            except Exception as e:
                logger.warning(f"LLM classification failed for email {email_id}: {e}")

            # Update status
            status = "completed" if not result["errors"] else "error"
            self.db.execute(
                "UPDATE emails SET status = ? WHERE id = ?", (status, email_id)
            )

            self._log(
                email_id=email_id,
                action="process_complete",
                status="success" if not result["errors"] else "warning",
                message=f"Saved {result['documents_saved']} docs, {result['invoices_downloaded']} invoices",
            )

        except Exception as e:
            logger.error(f"Pipeline error for email {email_id}: {e}")
            self.db.execute(
                "UPDATE emails SET status = 'error' WHERE id = ?", (email_id,)
            )
            result["errors"].append(str(e))

        return result

    async def _process_attachment(
        self, email_id: int, parsed: ParsedEmail, attachment: Attachment
    ) -> Optional[int]:
        """Process and store a single attachment."""
        # Build storage path
        stored_path = self._build_storage_path(parsed, attachment.filename)
        stored_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        stored_path.write_bytes(attachment.content)

        # Compute hash
        file_hash = hash_file(str(stored_path))

        # Get PDF metadata
        page_count = 0
        ocr_text = ""
        if attachment.content_type == "application/pdf" or attachment.filename.lower().endswith(".pdf"):
            try:
                page_count = get_pdf_page_count(str(stored_path))
                # Try embedded text first
                ocr_text = extract_pdf_text(str(stored_path))
                # Fall back to OCR if no embedded text
                if not ocr_text.strip() and self.settings.ocr.enabled:
                    ocr_text = ocr_pdf(str(stored_path), self.settings.ocr)
            except Exception as e:
                logger.warning(f"PDF processing error for {attachment.filename}: {e}")

        # Classify document
        classification = ""
        category = ""
        summary = ""
        try:
            classifier = self._get_classifier()
            text_for_classification = ocr_text[:2000] if ocr_text else attachment.filename
            classification = await classifier.classify_document(
                filename=attachment.filename,
                text_content=text_for_classification,
                email_subject=parsed.subject,
            )
            category = await classifier.categorize_document(
                filename=attachment.filename,
                classification=classification,
            )
            if ocr_text:
                summary = await classifier.summarize_text(ocr_text[:2000])
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

        # Store in database
        doc_id = self.db.execute_insert(
            """INSERT INTO documents
            (email_id, original_filename, stored_filename, stored_path,
             file_size, mime_type, sha256_hash, hash_verified, source_type,
             classification, category, ocr_text, ocr_completed, llm_summary, page_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email_id,
                attachment.filename,
                stored_path.name,
                str(stored_path),
                attachment.size,
                attachment.content_type,
                file_hash,
                1,  # hash verified on write
                "attachment",
                classification,
                category,
                ocr_text,
                1 if ocr_text else 0,
                summary,
                page_count,
            ),
        )

        self._log(
            email_id=email_id,
            document_id=doc_id,
            action="attachment_saved",
            status="success",
            message=f"Saved '{attachment.filename}' ({attachment.size} bytes, hash={file_hash[:16]}...)",
        )

        return doc_id

    async def _process_invoice_link(
        self, email_id: int, parsed: ParsedEmail, link: str
    ) -> Optional[int]:
        """Download and process an invoice from a link."""
        result = await download_invoice_from_link(link)
        if not result:
            return None

        filename = result["filename"]
        content = result["content"]
        content_type = result["content_type"]

        # Only process PDFs
        if not (content_type == "application/pdf" or filename.lower().endswith(".pdf")):
            logger.info(f"Skipping non-PDF invoice link: {link}")
            return None

        stored_path = self._build_storage_path(parsed, filename)
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(content)

        file_hash = hash_file(str(stored_path))

        # OCR and classify
        page_count = get_pdf_page_count(str(stored_path))
        ocr_text = extract_pdf_text(str(stored_path))
        if not ocr_text.strip() and self.settings.ocr.enabled:
            ocr_text = ocr_pdf(str(stored_path), self.settings.ocr)

        classification = "invoice"
        category = "financial"
        summary = ""
        try:
            classifier = self._get_classifier()
            if ocr_text:
                summary = await classifier.summarize_text(ocr_text[:2000])
        except Exception:
            pass

        doc_id = self.db.execute_insert(
            """INSERT INTO documents
            (email_id, original_filename, stored_filename, stored_path,
             file_size, mime_type, sha256_hash, hash_verified, source_type,
             source_url, classification, category, ocr_text, ocr_completed,
             llm_summary, page_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email_id, filename, stored_path.name, str(stored_path),
                len(content), content_type, file_hash, 1, "invoice_link",
                link, classification, category, ocr_text,
                1 if ocr_text else 0, summary, page_count,
            ),
        )

        self._log(
            email_id=email_id,
            document_id=doc_id,
            action="invoice_downloaded",
            status="success",
            message=f"Downloaded invoice '{filename}' from {link}",
        )

        return doc_id

    def _build_storage_path(self, parsed: ParsedEmail, filename: str) -> Path:
        """
        Build the storage path following the naming convention:
        {base_dir}/{email}/{date}/{sender}/{subject}/{filename}
        """
        base = Path(self.settings.storage.base_dir)

        # Email account
        email_dir = self._sanitize_name(parsed.sender_email.split("@")[0] + "_" + parsed.sender_email.split("@")[-1] if "@" in parsed.sender_email else "unknown")

        # Date
        date_str = "unknown_date"
        if parsed.date_sent:
            date_str = parsed.date_sent.strftime(self.settings.storage.date_format)

        # Sender
        sender = parsed.sender_name or parsed.sender_email
        sender_dir = self._sanitize_name(sender)

        # Subject
        subject_dir = self._sanitize_name(parsed.subject or "no_subject")

        # Build full path
        path = base / email_dir / date_str / sender_dir / subject_dir / self._sanitize_name(filename)

        # Handle duplicates
        if path.exists():
            stem = path.stem
            suffix = path.suffix
            counter = 1
            while path.exists():
                path = path.parent / f"{stem}_{counter}{suffix}"
                counter += 1

        return path

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a string for use as a directory/file name."""
        # Replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = sanitized.strip('._')
        # Limit length
        max_len = self.settings.storage.max_filename_length
        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len]
        return sanitized or "unnamed"

    def _is_processable(self, attachment: Attachment) -> bool:
        """Check if an attachment should be processed."""
        # Currently focusing on PDFs
        if attachment.content_type == "application/pdf":
            return True
        if attachment.filename.lower().endswith(".pdf"):
            return True
        return False

    def _log(self, action: str, status: str, message: str,
             email_id: int = None, document_id: int = None, account_id: str = None):
        """Write to ingestion log."""
        self.db.execute_insert(
            """INSERT INTO ingestion_logs
            (account_id, email_id, document_id, action, status, message)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, email_id, document_id, action, status, message),
        )

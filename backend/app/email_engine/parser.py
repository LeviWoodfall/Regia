"""
Email message parser for Regia.
Extracts metadata, body text, attachments, and invoice links from raw email messages.
"""

import os
import re
import email
import logging
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("regia.email.parser")


@dataclass
class Attachment:
    """Represents an email attachment."""
    filename: str
    content_type: str
    content: bytes
    size: int
    content_id: str = ""


@dataclass
class ParsedEmail:
    """Fully parsed email message."""
    message_id: str = ""
    subject: str = ""
    sender_email: str = ""
    sender_name: str = ""
    recipients: List[str] = field(default_factory=list)
    date_sent: Optional[datetime] = None
    body_text: str = ""
    body_html: str = ""
    attachments: List[Attachment] = field(default_factory=list)
    invoice_links: List[str] = field(default_factory=list)
    raw_headers: str = ""
    has_pdf: bool = False


# Patterns for detecting invoice/document download links
INVOICE_LINK_PATTERNS = [
    r'https?://[^\s<>"]+(?:invoice|receipt|statement|bill|document|download|pdf)[^\s<>"]*',
    r'https?://[^\s<>"]+\.pdf(?:\?[^\s<>"]*)?',
    r'https?://[^\s<>"]+/(?:download|get|fetch|view)/[^\s<>"]+',
]


def parse_email_message(raw_bytes: bytes) -> ParsedEmail:
    """
    Parse a raw email message into a structured ParsedEmail object.
    Extracts all metadata, body content, attachments, and invoice links.
    """
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    parsed = ParsedEmail()

    # === Headers ===
    parsed.message_id = msg.get("Message-ID", "").strip()
    parsed.subject = msg.get("Subject", "").strip()

    # Sender
    sender_name, sender_email = parseaddr(msg.get("From", ""))
    parsed.sender_name = sender_name or ""
    parsed.sender_email = sender_email or ""

    # Recipients
    for header in ["To", "Cc"]:
        value = msg.get(header, "")
        if value:
            for _, addr in email.utils.getaddresses([value]):
                if addr:
                    parsed.recipients.append(addr)

    # Date
    date_str = msg.get("Date", "")
    if date_str:
        try:
            parsed.date_sent = parsedate_to_datetime(date_str)
        except Exception:
            parsed.date_sent = None

    # Raw headers for storage
    parsed.raw_headers = str(msg.items())

    # === Body and Attachments ===
    _extract_parts(msg, parsed)

    # === Invoice Link Detection ===
    text_to_scan = parsed.body_text + " " + parsed.body_html
    parsed.invoice_links = _extract_invoice_links(text_to_scan)

    # Check for PDF attachments
    parsed.has_pdf = any(
        a.content_type == "application/pdf" or a.filename.lower().endswith(".pdf")
        for a in parsed.attachments
    )

    logger.info(
        f"Parsed email: subject='{parsed.subject}', "
        f"from='{parsed.sender_email}', "
        f"attachments={len(parsed.attachments)}, "
        f"invoice_links={len(parsed.invoice_links)}"
    )

    return parsed


def _extract_parts(msg: EmailMessage, parsed: ParsedEmail):
    """Recursively extract body text, HTML, and attachments from email parts."""
    if msg.is_multipart():
        for part in msg.iter_parts():
            _extract_parts(part, parsed)
    else:
        content_type = msg.get_content_type()
        disposition = msg.get_content_disposition()

        if disposition == "attachment" or (
            disposition == "inline" and content_type not in ("text/plain", "text/html")
        ):
            # This is an attachment
            try:
                content = msg.get_content()
                if isinstance(content, str):
                    content = content.encode()
                filename = msg.get_filename() or f"attachment_{len(parsed.attachments)}"
                parsed.attachments.append(Attachment(
                    filename=_sanitize_filename(filename),
                    content_type=content_type,
                    content=content,
                    size=len(content),
                    content_id=msg.get("Content-ID", "").strip("<>"),
                ))
            except Exception as e:
                logger.warning(f"Failed to extract attachment: {e}")
        elif content_type == "text/plain":
            try:
                parsed.body_text += msg.get_content() or ""
            except Exception:
                pass
        elif content_type == "text/html":
            try:
                parsed.body_html += msg.get_content() or ""
            except Exception:
                pass


def _extract_invoice_links(text: str) -> List[str]:
    """Extract potential invoice/document download links from email text."""
    links = set()
    for pattern in INVOICE_LINK_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        links.update(matches)

    # Also extract all links and filter for likely invoice URLs
    all_urls = re.findall(r'https?://[^\s<>"\']+', text)
    invoice_keywords = [
        "invoice", "receipt", "statement", "bill", "download",
        "pdf", "document", "payment", "order", "confirmation",
    ]
    for url in all_urls:
        url_lower = url.lower()
        if any(kw in url_lower for kw in invoice_keywords):
            links.add(url.rstrip(".,;:)>"))

    return list(links)


def _sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe filesystem storage."""
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    # Limit length
    if len(sanitized) > 200:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:200 - len(ext)] + ext
    return sanitized.strip('. ')



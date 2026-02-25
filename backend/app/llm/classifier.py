"""
Document and email classifier for Regia.
Uses lightweight LLM with fallback to rule-based classification.
"""

import re
import logging
from typing import Optional

from app.config import LLMConfig
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger("regia.llm.classifier")

# Rule-based fallback classifications
CLASSIFICATION_RULES = {
    "invoice": ["invoice", "bill", "payment due", "amount due", "total due", "tax invoice"],
    "receipt": ["receipt", "payment received", "thank you for your payment", "transaction"],
    "statement": ["statement", "account summary", "balance", "opening balance"],
    "contract": ["contract", "agreement", "terms and conditions", "hereby agree"],
    "report": ["report", "analysis", "summary", "quarterly", "annual", "monthly"],
    "correspondence": ["dear", "regards", "sincerely", "letter", "notice"],
    "shipping": ["shipping", "tracking", "delivery", "shipment", "dispatch"],
    "insurance": ["insurance", "policy", "premium", "claim", "coverage"],
    "tax": ["tax return", "tax form", "w-2", "1099", "ato", "tax assessment"],
    "legal": ["legal", "court", "lawsuit", "subpoena", "affidavit"],
    "medical": ["medical", "prescription", "diagnosis", "patient", "healthcare"],
    "payslip": ["payslip", "pay stub", "salary", "wages", "earnings"],
}

CATEGORY_MAP = {
    "invoice": "financial",
    "receipt": "financial",
    "statement": "financial",
    "contract": "legal",
    "report": "business",
    "correspondence": "communication",
    "shipping": "logistics",
    "insurance": "financial",
    "tax": "financial",
    "legal": "legal",
    "medical": "personal",
    "payslip": "financial",
}


class DocumentClassifier:
    """Classifies documents using LLM with rule-based fallback."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OllamaClient(config)
        self._llm_available: Optional[bool] = None

    async def _check_llm(self) -> bool:
        """Check if LLM is available (cached)."""
        if self._llm_available is None:
            self._llm_available = await self.client.is_available()
        return self._llm_available

    async def classify_document(
        self, filename: str, text_content: str = "", email_subject: str = ""
    ) -> str:
        """
        Classify a document into a type (invoice, receipt, contract, etc.).
        Uses LLM if available, falls back to rule-based classification.
        """
        if await self._check_llm():
            try:
                prompt = (
                    f"Classify this document into exactly ONE category. "
                    f"Categories: invoice, receipt, statement, contract, report, "
                    f"correspondence, shipping, insurance, tax, legal, medical, payslip, other.\n\n"
                    f"Filename: {filename}\n"
                    f"Email subject: {email_subject}\n"
                    f"Content preview: {text_content[:500]}\n\n"
                    f"Respond with ONLY the category name, nothing else."
                )
                result = await self.client.generate(prompt)
                classification = result.strip().lower().split()[0] if result else ""
                if classification in CLASSIFICATION_RULES or classification == "other":
                    return classification
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")

        if self.config.fallback_to_rules:
            return self._rule_based_classify(filename, text_content, email_subject)
        return "other"

    async def categorize_document(self, filename: str, classification: str) -> str:
        """Map a classification to a broader category."""
        return CATEGORY_MAP.get(classification, "general")

    async def classify_email(
        self, subject: str, sender: str, body_preview: str
    ) -> str:
        """Classify an email's content type."""
        if await self._check_llm():
            try:
                prompt = (
                    f"Classify this email into ONE category: "
                    f"invoice, newsletter, notification, personal, business, "
                    f"shipping, financial, marketing, other.\n\n"
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Preview: {body_preview[:300]}\n\n"
                    f"Respond with ONLY the category name."
                )
                result = await self.client.generate(prompt)
                return result.strip().lower().split()[0] if result else "other"
            except Exception:
                pass

        return self._rule_based_classify_email(subject, sender, body_preview)

    async def summarize_text(self, text: str) -> str:
        """Generate a brief summary of text content."""
        if not text.strip():
            return ""

        if await self._check_llm():
            try:
                prompt = (
                    f"Summarize this document in 1-2 sentences:\n\n"
                    f"{text[:1500]}\n\n"
                    f"Summary:"
                )
                result = await self.client.generate(prompt)
                return result.strip() if result else ""
            except Exception:
                pass

        # Fallback: return first 200 chars
        return text[:200].strip() + "..." if len(text) > 200 else text.strip()

    def _rule_based_classify(
        self, filename: str, text_content: str, email_subject: str
    ) -> str:
        """Rule-based document classification using keyword matching."""
        combined = f"{filename} {text_content} {email_subject}".lower()
        scores = {}
        for classification, keywords in CLASSIFICATION_RULES.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[classification] = score

        if scores:
            return max(scores, key=scores.get)
        return "other"

    def _rule_based_classify_email(
        self, subject: str, sender: str, body_preview: str
    ) -> str:
        """Rule-based email classification."""
        combined = f"{subject} {sender} {body_preview}".lower()

        if any(kw in combined for kw in ["invoice", "bill", "payment"]):
            return "invoice"
        if any(kw in combined for kw in ["newsletter", "unsubscribe", "weekly digest"]):
            return "newsletter"
        if any(kw in combined for kw in ["shipped", "tracking", "delivery"]):
            return "shipping"
        if any(kw in combined for kw in ["noreply", "notification", "alert"]):
            return "notification"
        return "other"

"""
Search engine for Regia.
Provides advanced full-text search across emails and documents using SQLite FTS5.
"""

import time
import logging
from typing import List, Dict, Any, Optional

from app.database import Database
from app.config import SearchConfig

logger = logging.getLogger("regia.search")


class SearchEngine:
    """
    Advanced search engine combining FTS5 full-text search with metadata filtering.
    Supports searching across emails, documents, OCR text, and LLM summaries.
    """

    def __init__(self, db: Database, config: SearchConfig):
        self.db = db
        self.config = config

    def search(
        self,
        query: str,
        scope: str = "all",
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Perform a full-text search across the document store.

        Args:
            query: Search query string
            scope: 'all', 'documents', or 'emails'
            filters: Optional dict of filters (date_from, date_to, classification, sender, etc.)
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Dict with results, total count, and timing info
        """
        start_time = time.time()
        results = []
        filters = filters or {}

        # Sanitize the FTS query
        fts_query = self._prepare_fts_query(query)

        if scope in ("all", "documents"):
            doc_results = self._search_documents(fts_query, filters)
            results.extend(doc_results)

        if scope in ("all", "emails"):
            email_results = self._search_emails(fts_query, filters)
            results.extend(email_results)

        # Sort by relevance (FTS rank)
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        total = len(results)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "results": paginated,
            "total": total,
            "query": query,
            "took_ms": round(elapsed_ms, 2),
            "page": page,
            "page_size": page_size,
        }

    def _search_documents(
        self, fts_query: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search documents using FTS5."""
        try:
            query = """
                SELECT d.id, d.original_filename, d.classification, d.category,
                       d.llm_summary, d.ocr_text, d.date_ingested, d.stored_path,
                       d.file_size, d.page_count, d.source_type, d.mime_type,
                       e.subject as email_subject, e.sender_name, e.sender_email,
                       e.date_sent,
                       rank
                FROM documents_fts fts
                JOIN documents d ON fts.rowid = d.id
                LEFT JOIN emails e ON d.email_id = e.id
                WHERE documents_fts MATCH ?
            """
            params = [fts_query]

            # Apply filters
            if filters.get("classification"):
                query += " AND d.classification = ?"
                params.append(filters["classification"])
            if filters.get("category"):
                query += " AND d.category = ?"
                params.append(filters["category"])
            if filters.get("date_from"):
                query += " AND d.date_ingested >= ?"
                params.append(filters["date_from"])
            if filters.get("date_to"):
                query += " AND d.date_ingested <= ?"
                params.append(filters["date_to"])
            if filters.get("sender"):
                query += " AND (e.sender_email LIKE ? OR e.sender_name LIKE ?)"
                sender_filter = f"%{filters['sender']}%"
                params.extend([sender_filter, sender_filter])

            query += " ORDER BY rank LIMIT ?"
            params.append(self.config.max_results)

            rows = self.db.execute(query, tuple(params))

            results = []
            for row in rows:
                snippet = self._generate_snippet(
                    row.get("ocr_text") or row.get("llm_summary") or "",
                    fts_query,
                )
                results.append({
                    "type": "document",
                    "id": row["id"],
                    "title": row["original_filename"],
                    "snippet": snippet,
                    "relevance_score": abs(row.get("rank", 0)),
                    "date": row["date_ingested"],
                    "metadata": {
                        "classification": row["classification"],
                        "category": row["category"],
                        "file_size": row["file_size"],
                        "page_count": row["page_count"],
                        "source_type": row["source_type"],
                        "email_subject": row.get("email_subject", ""),
                        "sender_name": row.get("sender_name", ""),
                        "sender_email": row.get("sender_email", ""),
                        "stored_path": row["stored_path"],
                    },
                })
            return results

        except Exception as e:
            logger.error(f"Document search error: {e}")
            return []

    def _search_emails(
        self, fts_query: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search emails using FTS5."""
        try:
            query = """
                SELECT e.id, e.subject, e.sender_name, e.sender_email,
                       e.date_sent, e.date_ingested, e.llm_summary, e.body_text,
                       e.classification, e.has_attachments, e.status,
                       rank
                FROM emails_fts fts
                JOIN emails e ON fts.rowid = e.id
                WHERE emails_fts MATCH ?
            """
            params = [fts_query]

            if filters.get("classification"):
                query += " AND e.classification = ?"
                params.append(filters["classification"])
            if filters.get("date_from"):
                query += " AND e.date_sent >= ?"
                params.append(filters["date_from"])
            if filters.get("date_to"):
                query += " AND e.date_sent <= ?"
                params.append(filters["date_to"])
            if filters.get("sender"):
                query += " AND (e.sender_email LIKE ? OR e.sender_name LIKE ?)"
                sender_filter = f"%{filters['sender']}%"
                params.extend([sender_filter, sender_filter])

            query += " ORDER BY rank LIMIT ?"
            params.append(self.config.max_results)

            rows = self.db.execute(query, tuple(params))

            results = []
            for row in rows:
                snippet = self._generate_snippet(
                    row.get("body_text") or row.get("llm_summary") or "",
                    fts_query,
                )
                results.append({
                    "type": "email",
                    "id": row["id"],
                    "title": row["subject"],
                    "snippet": snippet,
                    "relevance_score": abs(row.get("rank", 0)),
                    "date": row["date_sent"] or row["date_ingested"],
                    "metadata": {
                        "sender_name": row["sender_name"],
                        "sender_email": row["sender_email"],
                        "classification": row["classification"],
                        "has_attachments": bool(row["has_attachments"]),
                        "status": row["status"],
                    },
                })
            return results

        except Exception as e:
            logger.error(f"Email search error: {e}")
            return []

    def _prepare_fts_query(self, query: str) -> str:
        """
        Prepare a user query for FTS5.
        Handles special characters and converts to FTS5 syntax.
        """
        # Remove FTS5 special characters that could cause syntax errors
        cleaned = query.replace('"', '').replace("'", "")
        # Split into terms and wrap in quotes for phrase matching
        terms = cleaned.split()
        if len(terms) == 1:
            return f'"{terms[0]}"*'  # Prefix search for single terms
        # For multiple terms, use OR to be more permissive
        return " OR ".join(f'"{term}"' for term in terms)

    def _generate_snippet(self, text: str, query: str, length: int = None) -> str:
        """Generate a text snippet with context around matching terms."""
        length = length or self.config.snippet_length
        if not text:
            return ""

        query_terms = query.replace('"', '').replace('*', '').lower().split()
        text_lower = text.lower()

        # Find the first occurrence of any query term
        best_pos = len(text)
        for term in query_terms:
            pos = text_lower.find(term.lower())
            if 0 <= pos < best_pos:
                best_pos = pos

        if best_pos == len(text):
            # No match found, return start of text
            return text[:length] + ("..." if len(text) > length else "")

        # Extract snippet centered on the match
        start = max(0, best_pos - length // 4)
        end = min(len(text), start + length)
        snippet = text[start:end]

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""

        return f"{prefix}{snippet}{suffix}"

    def get_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = set()

        # Search document filenames
        try:
            rows = self.db.execute(
                "SELECT DISTINCT original_filename FROM documents WHERE original_filename LIKE ? LIMIT ?",
                (f"%{partial_query}%", limit),
            )
            for row in rows:
                suggestions.add(row["original_filename"])
        except Exception:
            pass

        # Search email subjects
        try:
            rows = self.db.execute(
                "SELECT DISTINCT subject FROM emails WHERE subject LIKE ? LIMIT ?",
                (f"%{partial_query}%", limit),
            )
            for row in rows:
                suggestions.add(row["subject"])
        except Exception:
            pass

        return list(suggestions)[:limit]

    def get_classifications(self) -> List[Dict[str, int]]:
        """Get all document classifications with counts."""
        try:
            return self.db.execute(
                """SELECT classification, COUNT(*) as count
                   FROM documents
                   WHERE classification != ''
                   GROUP BY classification
                   ORDER BY count DESC"""
            )
        except Exception:
            return []

    def get_categories(self) -> List[Dict[str, int]]:
        """Get all document categories with counts."""
        try:
            return self.db.execute(
                """SELECT category, COUNT(*) as count
                   FROM documents
                   WHERE category != ''
                   GROUP BY category
                   ORDER BY count DESC"""
            )
        except Exception:
            return []

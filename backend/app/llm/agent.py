"""
Reggie - The Regia AI Agent.
Conversational assistant for searching and finding documents/data.
Uses RAG (Retrieval Augmented Generation) over indexed documents.
"""

import logging
import secrets
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import LLMConfig
from app.database import Database
from app.llm.ollama_client import OllamaClient
from app.llm.learning import ReggieLearning

logger = logging.getLogger("regia.llm.agent")

SYSTEM_PROMPT = """You are Reggie, the AI assistant for Regia - a document management system.
Your role is to help users find documents, emails, and information from their ingested data.
You learn from every conversation and remember what the user tells you across sessions.
You also learn from ingested documents to build a knowledge base about the user's data.

Guidelines:
- Be concise and helpful
- When referencing documents, include their filename, date, and sender
- If you're unsure, say so rather than guessing
- You can search through emails, documents, OCR text, and classifications
- Always cite your sources when providing information from documents
- Use your memories about the user to personalize responses
- Reference knowledge you've extracted from their documents when relevant
- Be warm and professional in tone

When the user asks about a document or information, search the available data and provide
relevant results with context."""


class ReggieAgent:
    """
    Reggie - conversational AI agent for document search and interaction.
    Uses RAG pattern: retrieve relevant documents, then generate response.
    """

    def __init__(self, db: Database, config: LLMConfig):
        self.db = db
        self.config = config
        self.client = OllamaClient(config)
        self.learning = ReggieLearning(db, config)
        self._available: Optional[bool] = None

    async def is_available(self) -> bool:
        """Check if Reggie's LLM backend is available (re-checks each time)."""
        self._available = await self.client.is_available()
        return self._available

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return Reggie's response.
        Uses RAG to find relevant documents for context.
        """
        if not session_id:
            session_id = secrets.token_hex(16)

        # Store user message
        self._save_message(session_id, "user", message)

        # 1. Retrieve relevant documents
        sources = self._search_documents(message)

        # 2. Get conversation history
        history = self._get_history(session_id, limit=6)

        # 3. Recall memories and knowledge
        memories = self.learning.recall_memories(message, limit=8)
        knowledge = self.learning.recall_knowledge(message, limit=10)
        memory_context = self.learning.build_memory_context(memories, knowledge)

        # 4. Build context from retrieved documents
        doc_context = self._build_context(sources)

        # 5. Generate response
        if await self.is_available():
            response = await self._generate_response(message, history, doc_context, memory_context)
        else:
            response = self._fallback_response(message, sources)

        # 6. Generate suggestions
        suggestions = self._generate_suggestions(message, sources)

        # Store assistant message
        self._save_message(session_id, "assistant", response)

        # 7. Learn from this conversation turn (async, non-blocking)
        learned = []
        if await self.is_available():
            try:
                learned = await self.learning.extract_memories(message, response, session_id)
            except Exception as e:
                logger.debug(f"Memory extraction skipped: {e}")

        return {
            "message": response,
            "session_id": session_id,
            "sources": sources[:5],
            "suggestions": suggestions,
            "learned": learned,
            "memory_count": len(memories),
            "knowledge_count": len(knowledge),
        }

    async def _generate_response(
        self, message: str, history: List[Dict], doc_context: str, memory_context: str = ""
    ) -> str:
        """Generate a response using the LLM with RAG context + memories + knowledge."""
        # Build chat messages
        messages = []

        # Add recent history
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Build the user message with all context layers
        context_parts = []
        if memory_context:
            context_parts.append(memory_context)
        if doc_context:
            context_parts.append(f"=== Relevant documents ===\n{doc_context}")

        user_prompt = message
        if context_parts:
            combined_context = "\n\n".join(context_parts)
            user_prompt = f"{combined_context}\n\nUser question: {message}"

        messages.append({"role": "user", "content": user_prompt})

        response = await self.client.chat(messages, system=SYSTEM_PROMPT)
        return response if response else "I'm having trouble generating a response right now. Please try again."

    def _fallback_response(self, message: str, sources: List[Dict]) -> str:
        """Generate a response without LLM using search results."""
        if not sources:
            return (
                "I couldn't find any documents matching your query. "
                "Try rephrasing your search or check if the documents have been ingested."
            )

        response_parts = [f"I found {len(sources)} relevant result(s):\n"]
        for i, source in enumerate(sources[:5], 1):
            response_parts.append(
                f"{i}. **{source.get('title', 'Unknown')}**\n"
                f"   - Type: {source.get('type', 'document')}\n"
                f"   - Date: {source.get('date', 'Unknown')}\n"
                f"   - Preview: {source.get('snippet', '')[:150]}...\n"
            )

        return "\n".join(response_parts)

    def _search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents relevant to the query using FTS."""
        sources = []

        # Search documents FTS
        try:
            doc_results = self.db.execute(
                """SELECT d.id, d.original_filename, d.classification, d.category,
                          d.llm_summary, d.ocr_text, d.date_ingested, d.stored_path,
                          d.source_type,
                          e.subject as email_subject, e.sender_name, e.sender_email
                   FROM documents_fts fts
                   JOIN documents d ON fts.rowid = d.id
                   LEFT JOIN emails e ON d.email_id = e.id
                   WHERE documents_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            )
            for doc in doc_results:
                sources.append({
                    "type": "document",
                    "id": doc["id"],
                    "title": doc["original_filename"],
                    "snippet": (doc["llm_summary"] or doc["ocr_text"] or "")[:200],
                    "date": doc["date_ingested"],
                    "classification": doc["classification"],
                    "category": doc["category"],
                    "email_subject": doc.get("email_subject", ""),
                    "sender": doc.get("sender_name") or doc.get("sender_email", ""),
                    "path": doc["stored_path"],
                })
        except Exception as e:
            logger.debug(f"Document FTS search error: {e}")

        # Search emails FTS
        try:
            email_results = self.db.execute(
                """SELECT e.id, e.subject, e.sender_name, e.sender_email,
                          e.date_sent, e.llm_summary, e.body_text, e.classification
                   FROM emails_fts fts
                   JOIN emails e ON fts.rowid = e.id
                   WHERE emails_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            )
            for em in email_results:
                sources.append({
                    "type": "email",
                    "id": em["id"],
                    "title": em["subject"],
                    "snippet": (em["llm_summary"] or em["body_text"] or "")[:200],
                    "date": em["date_sent"] or "",
                    "classification": em["classification"] or "",
                    "sender": em["sender_name"] or em["sender_email"],
                })
        except Exception as e:
            logger.debug(f"Email FTS search error: {e}")

        return sources

    def _build_context(self, sources: List[Dict], max_chars: int = 2000) -> str:
        """Build a context string from retrieved sources."""
        if not sources:
            return ""

        parts = []
        char_count = 0
        for source in sources[:5]:
            entry = (
                f"[{source['type'].upper()}] {source['title']}\n"
                f"From: {source.get('sender', 'Unknown')} | Date: {source.get('date', 'Unknown')}\n"
                f"Content: {source.get('snippet', '')}\n"
            )
            if char_count + len(entry) > max_chars:
                break
            parts.append(entry)
            char_count += len(entry)

        return "\n---\n".join(parts)

    def _get_history(self, session_id: str, limit: int = 6) -> List[Dict]:
        """Get recent chat history for a session."""
        rows = self.db.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        return list(reversed(rows))

    def _save_message(self, session_id: str, role: str, content: str):
        """Save a chat message to history."""
        self.db.execute_insert(
            "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )

    def _generate_suggestions(self, message: str, sources: List[Dict]) -> List[str]:
        """Generate follow-up suggestions based on the conversation."""
        suggestions = []

        if sources:
            types = set(s.get("classification", "") for s in sources if s.get("classification"))
            if types:
                suggestions.append(f"Show me all {list(types)[0]} documents")

            senders = set(s.get("sender", "") for s in sources if s.get("sender"))
            if senders:
                sender = list(senders)[0]
                suggestions.append(f"Find more documents from {sender}")

        if not suggestions:
            suggestions = [
                "Show me recent invoices",
                "What documents came in today?",
                "Search for tax documents",
            ]

        return suggestions[:3]

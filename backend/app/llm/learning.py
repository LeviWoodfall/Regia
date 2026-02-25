"""
Reggie Learning Module.
Handles memory extraction from conversations and knowledge extraction from documents.
Enables Reggie to learn and remember across sessions.
"""

import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.database import Database
from app.llm.ollama_client import OllamaClient
from app.config import LLMConfig

logger = logging.getLogger("regia.llm.learning")

# Prompt for extracting memorable facts from conversations
MEMORY_EXTRACTION_PROMPT = """Extract facts from what the USER said below.

USER: {user_message}

Extract ONLY facts explicitly stated by the user. Examples of types:
- fact: "User's name is John", "User runs a company called X"
- preference: "User prefers invoices grouped by sender"
- instruction: "User wants tax docs flagged as important"

If nothing memorable was said, return: []

Return JSON array: [{{"content": "...", "type": "fact|preference|instruction|correction"}}]
JSON only, no other text:"""

# Prompt for extracting knowledge from documents
KNOWLEDGE_EXTRACTION_PROMPT = """Extract key facts and entities from this document text. Focus on:
- Named entities (people, companies, organizations)
- Financial amounts and currencies
- Important dates and deadlines
- Key terms and topics
- Relationships between entities

Document: {filename}
Classification: {classification}
Text (first 1500 chars):
{text}

Return a JSON array of objects. Each object has:
- "subject": the main entity or topic
- "predicate": the relationship or property (e.g. "sent_invoice_to", "amount", "date", "is_about")
- "object": the value or related entity
- "type": one of "entity", "amount", "date", "summary", "relationship", "key_term"

Extract up to 10 key facts. If the text is too short or unclear, return fewer.
Return ONLY the JSON array, no other text."""

# Prompt for extracting knowledge from emails
EMAIL_KNOWLEDGE_PROMPT = """Extract key facts from this email:

Subject: {subject}
From: {sender}
Date: {date}
Body (first 1000 chars):
{body}

Return a JSON array of objects with:
- "subject": main entity/topic
- "predicate": relationship/property
- "object": value/related entity
- "type": one of "entity", "amount", "date", "summary", "relationship", "key_term"

Focus on actionable information: who sent what, amounts mentioned, deadlines, key topics.
Extract up to 8 key facts. Return ONLY the JSON array."""


class ReggieLearning:
    """
    Handles Reggie's learning capabilities:
    - Extract and store memories from conversations
    - Extract and store knowledge from ingested documents/emails
    - Recall relevant memories and knowledge for context
    """

    def __init__(self, db: Database, config: LLMConfig):
        self.db = db
        self.config = config
        self.client = OllamaClient(config)

    # ── Memory Management ─────────────────────────────────────────────

    async def extract_memories(
        self, user_message: str, assistant_message: str, session_id: str
    ) -> List[Dict]:
        """Extract memorable facts from a conversation turn and store them."""
        memories = []

        # Try LLM extraction first
        try:
            prompt = MEMORY_EXTRACTION_PROMPT.format(
                user_message=user_message[:500],
            )
            response = await self.client.generate(prompt, system="You are a precise fact extractor. Return only valid JSON.")
            memories = self._parse_json_array(response)
        except Exception as e:
            logger.debug(f"LLM memory extraction failed: {e}")

        # Fall back to rule-based extraction if LLM returned nothing
        if not memories:
            memories = self._extract_memories_rules(user_message)

        # Store extracted memories
        stored = []
        for mem in memories:
            content = mem.get("content", "").strip()
            mem_type = mem.get("type", "fact")
            if not content or len(content) < 5:
                continue
            # Avoid duplicates
            if self._memory_exists(content):
                continue
            mem_id = self.db.execute_insert(
                """INSERT INTO reggie_memory (memory_type, content, source, source_id, confidence)
                   VALUES (?, ?, 'conversation', ?, ?)""",
                (mem_type, content, session_id, mem.get("confidence", 0.8)),
            )
            stored.append({"id": mem_id, "content": content, "type": mem_type})
            logger.info(f"Reggie learned: [{mem_type}] {content}")

        return stored

    def _extract_memories_rules(self, text: str) -> List[Dict]:
        """Rule-based fallback for extracting facts from user messages."""
        memories = []
        text_lower = text.lower().strip()

        # Name patterns (case-insensitive prefix, but validate name is capitalized)
        name_patterns = [
            r"(?:my name is|i'm|i am|call me)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
            r"(?:this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        ]
        stop_words = {"me", "the", "this", "that", "and", "or", "but", "so", "a", "an", "it", "i"}
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                # Remove trailing stop words
                name_parts = name.split()
                while name_parts and name_parts[-1].lower() in stop_words:
                    name_parts.pop()
                name = " ".join(name_parts)
                if len(name) > 1 and name.lower() not in stop_words:
                    memories.append({"content": f"User's name is {name}", "type": "fact", "confidence": 0.9})
                    break

        # Company/business patterns
        biz_patterns = [
            r"(?:my (?:company|business|firm|organization|org) (?:is|called|named))\s+(.+?)(?:\.|,|$)",
            r"(?:i (?:run|own|manage|work at|work for))\s+(?:a (?:company|business|firm) (?:called|named)\s+)?(.+?)(?:\.|,|$)",
            r"(?:called|named)\s+([A-Z][A-Za-z\s&]+?)(?:\.|,|\s+and\s|\s+which|\s+that|$)",
        ]
        for pat in biz_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                biz = m.group(1).strip().rstrip(".")
                if len(biz) > 2 and len(biz) < 60:
                    memories.append({"content": f"User's business/company is {biz}", "type": "fact", "confidence": 0.85})
                    break

        # Document type preferences
        doc_types = re.findall(
            r"\b(invoice|contract|receipt|tax|insurance|legal|medical|financial|accounting)\w*\b",
            text_lower,
        )
        if doc_types:
            unique = list(dict.fromkeys(doc_types))
            memories.append({
                "content": f"User works with {', '.join(unique)} documents",
                "type": "fact",
                "confidence": 0.75,
            })

        # Preference patterns
        pref_patterns = [
            (r"(?:i (?:prefer|like|want|need))\s+(.+?)(?:\.|$)", "preference"),
            (r"(?:always|please always)\s+(.+?)(?:\.|$)", "instruction"),
            (r"(?:never|don't|do not)\s+(.+?)(?:\.|$)", "instruction"),
            (r"(?:remember that|keep in mind|note that)\s+(.+?)(?:\.|$)", "instruction"),
        ]
        for pat, mem_type in pref_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                value = m.group(1).strip().rstrip(".")
                if len(value) > 5 and len(value) < 150:
                    memories.append({"content": f"User: {m.group(0).strip().rstrip('.')}", "type": mem_type, "confidence": 0.8})

        return memories

    def _memory_exists(self, content: str) -> bool:
        """Check if a similar memory already exists using FTS."""
        try:
            # Extract key words for fuzzy matching
            words = re.findall(r'\b\w{4,}\b', content.lower())
            if not words:
                return False
            query = " OR ".join(words[:5])
            results = self.db.execute(
                """SELECT m.content FROM reggie_memory_fts fts
                   JOIN reggie_memory m ON fts.rowid = m.id
                   WHERE reggie_memory_fts MATCH ?
                   LIMIT 5""",
                (query,),
            )
            # Simple similarity check — if >60% of words match, consider it duplicate
            for row in results:
                existing = set(re.findall(r'\b\w{4,}\b', row["content"].lower()))
                new_words = set(words)
                overlap = len(existing & new_words)
                if overlap >= len(new_words) * 0.6:
                    return True
            return False
        except Exception:
            return False

    def recall_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Recall relevant memories for a given query."""
        memories = []
        try:
            # FTS search
            words = re.findall(r'\b\w{3,}\b', query.lower())
            if words:
                fts_query = " OR ".join(words[:8])
                results = self.db.execute(
                    """SELECT m.id, m.memory_type, m.content, m.confidence, m.created_at
                       FROM reggie_memory_fts fts
                       JOIN reggie_memory m ON fts.rowid = m.id
                       WHERE reggie_memory_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (fts_query, limit),
                )
                for row in results:
                    memories.append(dict(row))
                    # Update access count
                    self.db.execute_insert(
                        "UPDATE reggie_memory SET access_count = access_count + 1, last_accessed_at = datetime('now') WHERE id = ?",
                        (row["id"],),
                    )
        except Exception as e:
            logger.debug(f"Memory recall error: {e}")

        # Also get recent high-confidence memories
        try:
            recent = self.db.execute(
                """SELECT id, memory_type, content, confidence, created_at
                   FROM reggie_memory
                   WHERE confidence >= 0.7
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (min(5, limit),),
            )
            seen_ids = {m["id"] for m in memories}
            for row in recent:
                if row["id"] not in seen_ids:
                    memories.append(dict(row))
        except Exception:
            pass

        return memories[:limit]

    def get_all_memories(self, limit: int = 50) -> List[Dict]:
        """Get all stored memories."""
        return self.db.execute(
            "SELECT * FROM reggie_memory ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a specific memory."""
        try:
            self.db.execute("DELETE FROM reggie_memory WHERE id = ?", (memory_id,))
            return True
        except Exception:
            return False

    def get_memory_stats(self) -> Dict:
        """Get memory statistics."""
        rows = self.db.execute(
            """SELECT
                COUNT(*) as total,
                SUM(CASE WHEN memory_type = 'fact' THEN 1 ELSE 0 END) as facts,
                SUM(CASE WHEN memory_type = 'preference' THEN 1 ELSE 0 END) as preferences,
                SUM(CASE WHEN memory_type = 'correction' THEN 1 ELSE 0 END) as corrections,
                SUM(CASE WHEN memory_type = 'instruction' THEN 1 ELSE 0 END) as instructions,
                SUM(CASE WHEN source = 'conversation' THEN 1 ELSE 0 END) as from_conversations,
                SUM(CASE WHEN source = 'document' THEN 1 ELSE 0 END) as from_documents
            FROM reggie_memory"""
        )
        return dict(rows[0]) if rows else {}

    # ── Knowledge Extraction ──────────────────────────────────────────

    async def extract_document_knowledge(
        self, document_id: int, filename: str, text: str,
        classification: str = "", email_id: Optional[int] = None,
    ) -> List[Dict]:
        """Extract knowledge from an ingested document and store it."""
        if not text or len(text.strip()) < 50:
            return []

        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(
                filename=filename,
                classification=classification,
                text=text[:1500],
            )
            response = await self.client.generate(prompt, system="You are a precise fact extractor. Return only valid JSON.")
            facts = self._parse_json_array(response)

            stored = []
            for fact in facts:
                subject = fact.get("subject", "").strip()
                predicate = fact.get("predicate", "").strip()
                obj = fact.get("object", "").strip()
                k_type = fact.get("type", "entity")
                if not subject or not obj:
                    continue

                k_id = self.db.execute_insert(
                    """INSERT INTO reggie_knowledge
                       (document_id, email_id, knowledge_type, subject, predicate, object, raw_text, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0.7)""",
                    (document_id, email_id, k_type, subject, predicate, obj, text[:200]),
                )
                stored.append({"id": k_id, "subject": subject, "predicate": predicate, "object": obj})

            if stored:
                logger.info(f"Extracted {len(stored)} knowledge facts from '{filename}'")
            return stored
        except Exception as e:
            logger.debug(f"Document knowledge extraction failed: {e}")
            return []

    async def extract_email_knowledge(
        self, email_id: int, subject: str, sender: str,
        date: str, body: str,
    ) -> List[Dict]:
        """Extract knowledge from an ingested email and store it."""
        if not body or len(body.strip()) < 30:
            return []

        try:
            prompt = EMAIL_KNOWLEDGE_PROMPT.format(
                subject=subject,
                sender=sender,
                date=date,
                body=body[:1000],
            )
            response = await self.client.generate(prompt, system="You are a precise fact extractor. Return only valid JSON.")
            facts = self._parse_json_array(response)

            stored = []
            for fact in facts:
                subj = fact.get("subject", "").strip()
                predicate = fact.get("predicate", "").strip()
                obj = fact.get("object", "").strip()
                k_type = fact.get("type", "entity")
                if not subj or not obj:
                    continue

                k_id = self.db.execute_insert(
                    """INSERT INTO reggie_knowledge
                       (email_id, knowledge_type, subject, predicate, object, raw_text, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, 0.7)""",
                    (email_id, k_type, subj, predicate, obj, body[:200]),
                )
                stored.append({"id": k_id, "subject": subj, "predicate": predicate, "object": obj})

            if stored:
                logger.info(f"Extracted {len(stored)} knowledge facts from email '{subject}'")
            return stored
        except Exception as e:
            logger.debug(f"Email knowledge extraction failed: {e}")
            return []

    def recall_knowledge(self, query: str, limit: int = 15) -> List[Dict]:
        """Recall relevant knowledge for a given query."""
        knowledge = []
        try:
            words = re.findall(r'\b\w{3,}\b', query.lower())
            if words:
                fts_query = " OR ".join(words[:8])
                results = self.db.execute(
                    """SELECT k.id, k.knowledge_type, k.subject, k.predicate, k.object,
                              k.document_id, k.email_id, k.confidence
                       FROM reggie_knowledge_fts fts
                       JOIN reggie_knowledge k ON fts.rowid = k.id
                       WHERE reggie_knowledge_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (fts_query, limit),
                )
                for row in results:
                    knowledge.append(dict(row))
        except Exception as e:
            logger.debug(f"Knowledge recall error: {e}")
        return knowledge

    def get_knowledge_stats(self) -> Dict:
        """Get knowledge base statistics."""
        rows = self.db.execute(
            """SELECT
                COUNT(*) as total,
                COUNT(DISTINCT document_id) as documents_indexed,
                COUNT(DISTINCT email_id) as emails_indexed,
                SUM(CASE WHEN knowledge_type = 'entity' THEN 1 ELSE 0 END) as entities,
                SUM(CASE WHEN knowledge_type = 'amount' THEN 1 ELSE 0 END) as amounts,
                SUM(CASE WHEN knowledge_type = 'date' THEN 1 ELSE 0 END) as dates,
                SUM(CASE WHEN knowledge_type = 'relationship' THEN 1 ELSE 0 END) as relationships
            FROM reggie_knowledge"""
        )
        return dict(rows[0]) if rows else {}

    # ── Utilities ─────────────────────────────────────────────────────

    def _parse_json_array(self, text: str) -> List[Dict]:
        """Parse a JSON array from LLM output, handling common formatting issues."""
        if not text:
            return []
        # Try to find JSON array in the response
        text = text.strip()
        # Look for array brackets
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        json_str = text[start:end + 1]
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return [item for item in result if isinstance(item, dict)]
        except json.JSONDecodeError:
            # Try fixing common issues
            json_str = json_str.replace("'", '"')
            try:
                result = json.loads(json_str)
                if isinstance(result, list):
                    return [item for item in result if isinstance(item, dict)]
            except json.JSONDecodeError:
                pass
        return []

    def build_memory_context(self, memories: List[Dict], knowledge: List[Dict], max_chars: int = 1500) -> str:
        """Build a context string from recalled memories and knowledge."""
        parts = []
        char_count = 0

        if memories:
            parts.append("=== Things I remember about you ===")
            for mem in memories[:8]:
                entry = f"- [{mem.get('memory_type', 'fact')}] {mem['content']}"
                if char_count + len(entry) > max_chars:
                    break
                parts.append(entry)
                char_count += len(entry)

        if knowledge and char_count < max_chars:
            parts.append("\n=== Relevant knowledge from your documents ===")
            for k in knowledge[:10]:
                entry = f"- {k['subject']} {k.get('predicate', '')} {k['object']}"
                if char_count + len(entry) > max_chars:
                    break
                parts.append(entry)
                char_count += len(entry)

        return "\n".join(parts)

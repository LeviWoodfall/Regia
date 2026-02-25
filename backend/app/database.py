"""
Database layer for Regia.
Uses SQLite for zero-config, self-contained storage.
Includes FTS5 virtual tables for full-text search.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from app.config import AppSettings


DB_SCHEMA = """
-- Email accounts (metadata only, credentials stored encrypted separately)
CREATE TABLE IF NOT EXISTS email_accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'imap',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Ingested emails
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES email_accounts(id),
    message_id TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    sender_email TEXT NOT NULL DEFAULT '',
    sender_name TEXT NOT NULL DEFAULT '',
    recipient TEXT NOT NULL DEFAULT '',
    date_sent TEXT,
    date_received TEXT,
    date_ingested TEXT NOT NULL DEFAULT (datetime('now')),
    body_text TEXT DEFAULT '',
    body_html TEXT DEFAULT '',
    has_attachments INTEGER NOT NULL DEFAULT 0,
    has_invoice_links INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, error
    classification TEXT DEFAULT '',
    llm_summary TEXT DEFAULT '',
    raw_headers TEXT DEFAULT '',
    UNIQUE(account_id, message_id)
);

-- Documents (attachments + downloaded invoices)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER REFERENCES emails(id),
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT DEFAULT '',
    sha256_hash TEXT NOT NULL,
    hash_verified INTEGER NOT NULL DEFAULT 0,
    source_type TEXT NOT NULL DEFAULT 'attachment',  -- attachment, invoice_link
    source_url TEXT DEFAULT '',
    classification TEXT DEFAULT '',
    category TEXT DEFAULT '',
    ocr_text TEXT DEFAULT '',
    ocr_completed INTEGER NOT NULL DEFAULT 0,
    llm_summary TEXT DEFAULT '',
    page_count INTEGER DEFAULT 0,
    date_ingested TEXT NOT NULL DEFAULT (datetime('now')),
    metadata_json TEXT DEFAULT '{}'
);

-- Full-text search index for documents
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    original_filename,
    ocr_text,
    llm_summary,
    classification,
    category,
    content='documents',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, original_filename, ocr_text, llm_summary, classification, category)
    VALUES (new.id, new.original_filename, new.ocr_text, new.llm_summary, new.classification, new.category);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, original_filename, ocr_text, llm_summary, classification, category)
    VALUES ('delete', old.id, old.original_filename, old.ocr_text, old.llm_summary, old.classification, old.category);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, original_filename, ocr_text, llm_summary, classification, category)
    VALUES ('delete', old.id, old.original_filename, old.ocr_text, old.llm_summary, old.classification, old.category);
    INSERT INTO documents_fts(rowid, original_filename, ocr_text, llm_summary, classification, category)
    VALUES (new.id, new.original_filename, new.ocr_text, new.llm_summary, new.classification, new.category);
END;

-- Full-text search index for emails
CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
    subject,
    sender_name,
    sender_email,
    body_text,
    llm_summary,
    content='emails',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
    INSERT INTO emails_fts(rowid, subject, sender_name, sender_email, body_text, llm_summary)
    VALUES (new.id, new.subject, new.sender_name, new.sender_email, new.body_text, new.llm_summary);
END;

CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
    INSERT INTO emails_fts(emails_fts, rowid, subject, sender_name, sender_email, body_text, llm_summary)
    VALUES ('delete', old.id, old.subject, old.sender_name, old.sender_email, old.body_text, old.llm_summary);
END;

CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
    INSERT INTO emails_fts(emails_fts, rowid, subject, sender_name, sender_email, body_text, llm_summary)
    VALUES ('delete', old.id, old.subject, old.sender_name, old.sender_email, old.body_text, old.llm_summary);
    INSERT INTO emails_fts(rowid, subject, sender_name, sender_email, body_text, llm_summary)
    VALUES (new.id, new.subject, new.sender_name, new.sender_email, new.body_text, new.llm_summary);
END;

-- Ingestion logs
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT,
    email_id INTEGER,
    document_id INTEGER,
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'info',  -- info, warning, error, success
    message TEXT NOT NULL DEFAULT '',
    details_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Chat history for Reggie agent
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    context_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Scheduler job tracking
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    job_type TEXT NOT NULL DEFAULT 'email_fetch',
    status TEXT NOT NULL DEFAULT 'idle',  -- idle, running, completed, failed
    last_run_at TEXT,
    next_run_at TEXT,
    last_error TEXT DEFAULT '',
    run_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Database:
    """SQLite database manager for Regia."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript(DB_SCHEMA)

    @contextmanager
    def get_connection(self):
        """Get a database connection with WAL mode and foreign keys."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return results."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an insert and return the last row id."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def execute_many(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets."""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)

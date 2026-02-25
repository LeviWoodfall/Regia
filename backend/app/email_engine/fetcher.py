"""
Email fetcher for Regia.
Orchestrates email retrieval, parsing, and handoff to the processing pipeline.
Enforces one-way data flow and handles pagination/batching.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.config import EmailAccountConfig
from app.database import Database
from app.email_engine.connector import IMAPConnector
from app.email_engine.parser import parse_email_message, ParsedEmail

logger = logging.getLogger("regia.email.fetcher")


class EmailFetcher:
    """
    Fetches and processes emails from configured IMAP accounts.
    All operations are strictly read-only.
    """

    def __init__(self, db: Database):
        self.db = db

    async def fetch_account(self, account: EmailAccountConfig) -> Dict[str, Any]:
        """
        Fetch new emails from a single account.
        Returns a summary of the fetch operation.
        """
        result = {
            "account_id": account.id,
            "account_email": account.email,
            "emails_found": 0,
            "emails_new": 0,
            "emails_processed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        connector = IMAPConnector(account)
        try:
            connected = await connector.connect()
            if not connected:
                result["errors"].append("Failed to connect to IMAP server")
                self._log(account.id, "fetch_failed", "error", "Connection failed")
                return result

            for folder in account.folders:
                try:
                    folder_result = await self._fetch_folder(connector, account, folder)
                    result["emails_found"] += folder_result["found"]
                    result["emails_new"] += folder_result["new"]
                    result["emails_processed"] += folder_result["processed"]
                    result["errors"].extend(folder_result["errors"])
                except Exception as e:
                    error_msg = f"Error fetching folder '{folder}': {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

        finally:
            connector.disconnect()

        result["finished_at"] = datetime.utcnow().isoformat()

        # Update last sync time
        self.db.execute(
            "UPDATE email_accounts SET last_sync_at = ?, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), account.id),
        )

        self._log(
            account.id, "fetch_complete", "success",
            f"Found {result['emails_new']} new emails, processed {result['emails_processed']}",
        )
        return result

    async def _fetch_folder(
        self, connector: IMAPConnector, account: EmailAccountConfig, folder: str
    ) -> Dict[str, Any]:
        """Fetch new emails from a specific folder."""
        result = {"found": 0, "new": 0, "processed": 0, "errors": []}

        count = connector.select_folder(folder)
        logger.info(f"Folder '{folder}' has {count} messages")

        # Search for unseen messages
        msg_ids = connector.search("UNSEEN")
        result["found"] = len(msg_ids)

        for msg_id in msg_ids:
            try:
                raw_msg = connector.fetch_message(msg_id)
                if not raw_msg:
                    continue

                parsed = parse_email_message(raw_msg)

                # Check if we already have this email
                existing = self.db.execute(
                    "SELECT id FROM emails WHERE account_id = ? AND message_id = ?",
                    (account.id, parsed.message_id),
                )
                if existing:
                    continue

                result["new"] += 1

                # Store email in database
                email_id = self._store_email(account.id, parsed)
                result["processed"] += 1

                logger.info(
                    f"Ingested email {parsed.message_id}: "
                    f"'{parsed.subject}' from {parsed.sender_email}"
                )

            except Exception as e:
                error_msg = f"Error processing message {msg_id}: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        return result

    def _store_email(self, account_id: str, parsed: ParsedEmail) -> int:
        """Store a parsed email in the database."""
        email_id = self.db.execute_insert(
            """INSERT INTO emails
            (account_id, message_id, subject, sender_email, sender_name,
             recipient, date_sent, body_text, body_html,
             has_attachments, has_invoice_links, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                account_id,
                parsed.message_id,
                parsed.subject,
                parsed.sender_email,
                parsed.sender_name,
                ", ".join(parsed.recipients),
                parsed.date_sent.isoformat() if parsed.date_sent else None,
                parsed.body_text,
                parsed.body_html,
                1 if parsed.attachments else 0,
                1 if parsed.invoice_links else 0,
                "pending",
            ),
        )
        return email_id

    def get_pending_emails(self) -> List[Dict[str, Any]]:
        """Get emails that are pending processing."""
        return self.db.execute(
            "SELECT * FROM emails WHERE status = 'pending' ORDER BY date_ingested ASC"
        )

    def _log(self, account_id: str, action: str, status: str, message: str):
        """Write to the ingestion log."""
        self.db.execute_insert(
            "INSERT INTO ingestion_logs (account_id, action, status, message) VALUES (?, ?, ?, ?)",
            (account_id, action, status, message),
        )

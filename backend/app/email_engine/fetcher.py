"""
Email fetcher for Regia.
Orchestrates email retrieval, parsing, and handoff to the processing pipeline.
Supports configurable search criteria, post-processing actions, and filtering.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.config import EmailAccountConfig
from app.database import Database
from app.email_engine.connector import IMAPConnector
from app.email_engine.parser import parse_email_message, ParsedEmail
from app.security import credential_manager

logger = logging.getLogger("regia.email.fetcher")


class EmailFetcher:
    """
    Fetches and processes emails from configured IMAP accounts.
    Supports configurable search, filtering, and post-processing actions.
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
            "emails_skipped": 0,
            "post_actions_applied": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        # Pre-check: credential store must be unlocked
        if not credential_manager.is_unlocked:
            result["errors"].append(
                "Credential store is locked. Unlock it in Settings → Security before fetching."
            )
            self._log(account.id, "fetch_failed", "error", "Credential store is locked")
            return result

        connector = IMAPConnector(account)
        try:
            connected = await connector.connect()
            if not connected:
                result["errors"].append("Failed to connect to IMAP server")
                self._log(account.id, "fetch_failed", "error", "Connection failed")
                return result

            # Determine if we need write access for post-processing
            needs_write = self._needs_write_access(account)

            for folder in account.folders:
                try:
                    folder_result = await self._fetch_folder(
                        connector, account, folder, needs_write
                    )
                    result["emails_found"] += folder_result["found"]
                    result["emails_new"] += folder_result["new"]
                    result["emails_processed"] += folder_result["processed"]
                    result["emails_skipped"] += folder_result["skipped"]
                    result["post_actions_applied"] += folder_result["post_actions"]
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
            f"Found {result['emails_new']} new, processed {result['emails_processed']}, "
            f"skipped {result['emails_skipped']}, post-actions {result['post_actions_applied']}",
        )
        return result

    def _needs_write_access(self, account: EmailAccountConfig) -> bool:
        """Check if the account config requires write access to the mailbox."""
        effective_action = self._get_effective_post_action(account)
        return effective_action != "none"

    def _get_effective_post_action(self, account: EmailAccountConfig) -> str:
        """Get the effective post-processing action, considering legacy fields."""
        if account.post_action != "none":
            return account.post_action
        # Legacy compat
        if account.mark_as_read:
            return "mark_read"
        if account.move_to_folder:
            return "move"
        return "none"

    def _get_effective_move_folder(self, account: EmailAccountConfig) -> str:
        """Get the effective move folder, considering legacy fields."""
        if account.post_action_folder:
            return account.post_action_folder
        return account.move_to_folder or ""

    async def _fetch_folder(
        self, connector: IMAPConnector, account: EmailAccountConfig,
        folder: str, needs_write: bool
    ) -> Dict[str, Any]:
        """Fetch new emails from a specific folder."""
        result = {"found": 0, "new": 0, "processed": 0, "skipped": 0, "post_actions": 0, "errors": []}

        count = connector.select_folder(folder, readonly=not needs_write)
        logger.info(f"Folder '{folder}' has {count} messages (write={needs_write})")

        # Use configured search criteria
        criteria = account.search_criteria or "UNSEEN"
        msg_ids = connector.search(criteria)
        result["found"] = len(msg_ids)

        # Apply max_emails_per_fetch limit
        limit = account.max_emails_per_fetch
        if limit and limit > 0 and len(msg_ids) > limit:
            msg_ids = msg_ids[:limit]
            logger.info(f"Limited to {limit} messages per fetch")

        # Calculate age cutoff if configured
        age_cutoff = None
        if account.skip_older_than_days and account.skip_older_than_days > 0:
            age_cutoff = datetime.utcnow() - timedelta(days=account.skip_older_than_days)

        effective_action = self._get_effective_post_action(account)
        move_folder = self._get_effective_move_folder(account)

        for msg_id in msg_ids:
            try:
                raw_msg = connector.fetch_message(msg_id)
                if not raw_msg:
                    continue

                parsed = parse_email_message(raw_msg)

                # Skip if older than cutoff
                if age_cutoff and parsed.date_sent and parsed.date_sent < age_cutoff:
                    result["skipped"] += 1
                    continue

                # Skip if only_with_attachments and no attachments
                if account.only_with_attachments and not parsed.attachments:
                    result["skipped"] += 1
                    continue

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

                # Apply post-processing action on the mail server
                if needs_write:
                    try:
                        self._apply_post_action(connector, msg_id, effective_action, move_folder)
                        result["post_actions"] += 1
                    except Exception as e:
                        logger.warning(f"Post-action '{effective_action}' failed for {msg_id}: {e}")

                logger.info(
                    f"Ingested email {parsed.message_id}: "
                    f"'{parsed.subject}' from {parsed.sender_email}"
                )

            except Exception as e:
                error_msg = f"Error processing message {msg_id}: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        return result

    def _apply_post_action(
        self, connector: IMAPConnector, msg_id: bytes, action: str, move_folder: str
    ):
        """Apply a post-processing action to a message on the mail server."""
        if action == "mark_read":
            connector.mark_as_read(msg_id)
        elif action == "move":
            if move_folder:
                connector.create_folder(move_folder)  # Ensure it exists
                connector.move_message(msg_id, move_folder)
            else:
                logger.warning("Post-action 'move' configured but no folder specified")
        elif action == "delete":
            connector.delete_message(msg_id)
        elif action == "archive":
            connector.archive_message(msg_id)

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

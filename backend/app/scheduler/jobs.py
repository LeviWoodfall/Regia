"""
Scheduler for Regia.
Manages periodic email fetching and document processing jobs.
Uses APScheduler for reliable background task scheduling.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from app.config import AppSettings, EmailAccountConfig
from app.database import Database

logger = logging.getLogger("regia.scheduler")


class EmailScheduler:
    """Manages scheduled email fetching and processing jobs."""

    def __init__(self, db: Database, settings: AppSettings):
        self.db = db
        self.settings = settings
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,
                "max_instances": settings.scheduler.max_concurrent_jobs,
                "misfire_grace_time": 300,
            },
        )
        self._running = False

    def start(self):
        """Start the scheduler and register jobs for all enabled accounts."""
        if self._running:
            return

        for account in self.settings.email_accounts:
            if account.enabled:
                self.add_account_job(account)

        self._scheduler.start()
        self._running = True
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    def add_account_job(self, account: EmailAccountConfig):
        """Add a scheduled job for an email account."""
        job_id = f"email_fetch_{account.id}"

        # Remove existing job if any
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        self._scheduler.add_job(
            self._fetch_job,
            trigger=IntervalTrigger(minutes=account.poll_interval_minutes),
            id=job_id,
            args=[account.id],
            name=f"Fetch {account.email}",
            replace_existing=True,
        )

        # Track in database
        self.db.execute_insert(
            """INSERT OR REPLACE INTO scheduler_jobs
            (id, account_id, job_type, status)
            VALUES (?, ?, 'email_fetch', 'idle')""",
            (job_id, account.id),
        )

        logger.info(
            f"Scheduled email fetch for {account.email} "
            f"every {account.poll_interval_minutes} minutes"
        )

    def remove_account_job(self, account_id: str):
        """Remove a scheduled job for an account."""
        job_id = f"email_fetch_{account_id}"
        try:
            self._scheduler.remove_job(job_id)
            self.db.execute(
                "DELETE FROM scheduler_jobs WHERE id = ?", (job_id,)
            )
            logger.info(f"Removed scheduled job for account {account_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")

    async def _fetch_job(self, account_id: str):
        """Execute a scheduled email fetch job."""
        job_id = f"email_fetch_{account_id}"

        # Update job status
        self.db.execute(
            "UPDATE scheduler_jobs SET status = 'running', last_run_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), job_id),
        )

        try:
            # Find the account config
            account = None
            for acc in self.settings.email_accounts:
                if acc.id == account_id:
                    account = acc
                    break

            if not account:
                logger.error(f"Account {account_id} not found in config")
                return

            # Import here to avoid circular imports
            from app.email_engine.fetcher import EmailFetcher
            from app.processing.pipeline import ProcessingPipeline
            from app.email_engine.parser import parse_email_message

            fetcher = EmailFetcher(self.db)
            pipeline = ProcessingPipeline(self.db, self.settings)

            # Fetch emails
            fetch_result = await fetcher.fetch_account(account)

            # Process pending emails
            pending = fetcher.get_pending_emails()
            for email_row in pending:
                if email_row["account_id"] == account_id:
                    # We need the parsed email for processing
                    # Re-parse from stored data
                    from app.email_engine.parser import ParsedEmail, Attachment
                    parsed = ParsedEmail(
                        message_id=email_row["message_id"],
                        subject=email_row["subject"],
                        sender_email=email_row["sender_email"],
                        sender_name=email_row["sender_name"],
                        body_text=email_row.get("body_text", ""),
                        body_html=email_row.get("body_html", ""),
                    )
                    if email_row.get("date_sent"):
                        try:
                            from datetime import datetime as dt
                            parsed.date_sent = dt.fromisoformat(email_row["date_sent"])
                        except Exception:
                            pass

                    await pipeline.process_email(email_row["id"], parsed)

            # Update job status
            self.db.execute(
                """UPDATE scheduler_jobs
                SET status = 'completed', last_error = '', run_count = run_count + 1
                WHERE id = ?""",
                (job_id,),
            )

            logger.info(
                f"Fetch job completed for {account.email}: "
                f"{fetch_result['emails_new']} new emails"
            )

        except Exception as e:
            logger.error(f"Fetch job failed for account {account_id}: {e}")
            self.db.execute(
                "UPDATE scheduler_jobs SET status = 'failed', last_error = ? WHERE id = ?",
                (str(e), job_id),
            )

    async def run_now(self, account_id: str) -> Dict[str, Any]:
        """Trigger an immediate fetch for an account."""
        logger.info(f"Manual fetch triggered for account {account_id}")
        await self._fetch_job(account_id)

        # Return latest job status
        rows = self.db.execute(
            "SELECT * FROM scheduler_jobs WHERE account_id = ?",
            (account_id,),
        )
        return rows[0] if rows else {}

    def get_job_status(self, account_id: str = None) -> list:
        """Get status of all or specific account jobs."""
        if account_id:
            return self.db.execute(
                "SELECT * FROM scheduler_jobs WHERE account_id = ?",
                (account_id,),
            )
        return self.db.execute("SELECT * FROM scheduler_jobs ORDER BY last_run_at DESC")

    @property
    def is_running(self) -> bool:
        return self._running

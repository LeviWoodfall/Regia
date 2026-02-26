"""
Email management routes for Regia.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from pathlib import Path

from app.models import EmailResponse, EmailListResponse
from app.email_engine.connector import IMAPConnector
from app.email_engine.parser import parse_email_message
from app.processing.pipeline import ProcessingPipeline
from app.email_engine.parser import Attachment, ParsedEmail
from datetime import datetime
from playwright.async_api import async_playwright

router = APIRouter(prefix="/api/emails", tags=["emails"])


def get_db():
    from app.main import app_state
    return app_state["db"]


def get_scheduler():
    from app.main import app_state
    return app_state["scheduler"]


def get_settings():
    from app.main import app_state
    return app_state["settings"]


@router.get("", response_model=EmailListResponse)
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    classification: Optional[str] = None,
    db=Depends(get_db),
):
    """List ingested emails with pagination and filtering."""
    query = "SELECT * FROM emails WHERE 1=1"
    count_query = "SELECT COUNT(*) as total FROM emails WHERE 1=1"
    params = []

    if account_id:
        query += " AND account_id = ?"
        count_query += " AND account_id = ?"
        params.append(account_id)
    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)
    if classification:
        query += " AND classification = ?"
        count_query += " AND classification = ?"
        params.append(classification)

    # Get total count
    total_rows = db.execute(count_query, tuple(params))
    total = total_rows[0]["total"] if total_rows else 0

    # Get paginated results
    offset = (page - 1) * page_size
    query += " ORDER BY date_ingested DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    rows = db.execute(query, tuple(params))

    emails = []
    for row in rows:
        # Get document count for this email
        doc_count = db.execute(
            "SELECT COUNT(*) as count FROM documents WHERE email_id = ?",
            (row["id"],),
        )
        emails.append(EmailResponse(
            id=row["id"],
            account_id=row["account_id"],
            message_id=row["message_id"],
            subject=row["subject"],
            sender_email=row["sender_email"],
            sender_name=row["sender_name"],
            date_sent=row["date_sent"],
            date_ingested=row["date_ingested"],
            has_attachments=bool(row["has_attachments"]),
            has_invoice_links=bool(row["has_invoice_links"]),
            status=row["status"],
            classification=row["classification"] or "",
            llm_summary=row["llm_summary"] or "",
            document_count=doc_count[0]["count"] if doc_count else 0,
        ))

    return EmailListResponse(
        emails=emails, total=total, page=page, page_size=page_size
    )


@router.get("/{email_id}")
async def get_email(email_id: int, db=Depends(get_db)):
    """Get a single email with its documents."""
    rows = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not rows:
        raise HTTPException(404, "Email not found")

    email_row = rows[0]
    documents = db.execute(
        "SELECT * FROM documents WHERE email_id = ?", (email_id,)
    )

    return {
        "email": email_row,
        "documents": documents,
    }


@router.post("/{email_id}/redownload")
async def redownload_email(
    email_id: int,
    db=Depends(get_db),
    settings=Depends(get_settings),
):
    """Re-fetch an email from the mail server by Message-ID and re-run processing with dedup."""
    rows = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not rows:
        raise HTTPException(404, "Email not found")
    email_row = rows[0]

    # Find account config
    account = next((a for a in settings.email_accounts if a.id == email_row["account_id"]), None)
    if not account:
        raise HTTPException(404, "Account not found for this email")

    connector = IMAPConnector(account)
    pipeline = ProcessingPipeline(db, settings)

    try:
        connected = await connector.connect()
        if not connected:
            raise HTTPException(500, "Failed to connect to IMAP server")

        # Search across configured folders by Message-ID
        msg_ids = []
        for folder in account.folders:
            connector.select_folder(folder, readonly=False)
            msg_ids = connector.search_by_header("Message-ID", email_row["message_id"])
            if msg_ids:
                break

        if not msg_ids:
            raise HTTPException(404, "Message not found on server")

        raw = connector.fetch_message(msg_ids[0])
        if not raw:
            raise HTTPException(500, "Failed to fetch message content")

        parsed = parse_email_message(raw)

        # Re-run processing for this email id
        result = await pipeline.process_email(email_id, parsed)
        return {"status": "ok", "result": result}

    finally:
        connector.disconnect()


async def _refresh_email(email_row, account, db, settings):
    connector = IMAPConnector(account)
    pipeline = ProcessingPipeline(db, settings)
    try:
        connected = await connector.connect()
        if not connected:
            return {"status": "error", "error": "connect_failed"}

        msg_ids = []
        for folder in account.folders:
            connector.select_folder(folder, readonly=False)
            msg_ids = connector.search_by_header("Message-ID", email_row["message_id"])
            if msg_ids:
                break

        if not msg_ids:
            return {"status": "error", "error": "not_found"}

        raw = connector.fetch_message(msg_ids[0])
        if not raw:
            return {"status": "error", "error": "fetch_failed"}

        parsed = parse_email_message(raw)
        result = await pipeline.process_email(email_row["id"], parsed)
        return {"status": "ok", "result": result}
    finally:
        connector.disconnect()


@router.post("/{email_id}/refresh")
async def refresh_email_files(
    email_id: int,
    db=Depends(get_db),
    settings=Depends(get_settings),
):
    """Re-fetch a single email and ensure attachments are stored on disk (dedupbed)."""
    rows = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not rows:
        raise HTTPException(404, "Email not found")
    email_row = rows[0]
    account = next((a for a in settings.email_accounts if a.id == email_row["account_id"]), None)
    if not account:
        raise HTTPException(404, "Account not found for this email")

    result = await _refresh_email(email_row, account, db, settings)
    if result.get("status") != "ok":
        raise HTTPException(500, f"Refresh failed: {result.get('error')}")
    return result


@router.post("/refresh-all-attachments")
async def refresh_all_attachments(db=Depends(get_db), settings=Depends(get_settings)):
    """Refresh attachments for all emails that have attachments (reprocess from IMAP)."""
    emails = db.execute("SELECT * FROM emails WHERE has_attachments = 1")
    if not emails:
        return {"status": "ok", "processed": 0, "errors": []}

    processed = 0
    errors = []
    for email_row in emails:
        account = next((a for a in settings.email_accounts if a.id == email_row["account_id"]), None)
        if not account:
            errors.append({"email_id": email_row["id"], "error": "account_not_found"})
            continue
        res = await _refresh_email(email_row, account, db, settings)
        if res.get("status") == "ok":
            processed += 1
        else:
            errors.append({"email_id": email_row["id"], "error": res.get("error")})

    return {"status": "ok", "processed": processed, "errors": errors}


@router.post("/{email_id}/capture-link")
async def capture_link_to_pdf(
    email_id: int,
    url: str,
    filename: str = "captured_link.pdf",
    db=Depends(get_db),
    settings=Depends(get_settings),
):
    """Fetch a link, render to PDF headlessly (Playwright), and store as an attachment."""
    rows = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not rows:
        raise HTTPException(404, "Email not found")
    email_row = rows[0]
    account = next((a for a in settings.email_accounts if a.id == email_row["account_id"]), None)
    if not account:
        raise HTTPException(404, "Account not found for this email")

    # Render page to PDF with Playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            pdf_bytes = await page.pdf(print_background=True)
            await browser.close()
    except Exception as e:
        raise HTTPException(500, f"Failed to capture link: {e}")

    # Build minimal ParsedEmail context
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
            parsed.date_sent = datetime.fromisoformat(email_row["date_sent"])
        except Exception:
            pass

    attach = Attachment(
        filename=filename,
        content_type="application/pdf",
        content=pdf_bytes,
        size=len(pdf_bytes),
    )

    pipeline = ProcessingPipeline(db, settings)
    doc_id = await pipeline._process_attachment(email_id, parsed, attach)

    return {"status": "ok", "document_id": doc_id}


@router.delete("/{email_id}")
async def delete_email(
    email_id: int,
    delete_remote: bool = Query(True, description="Also delete from mail server"),
    db=Depends(get_db),
    settings=Depends(get_settings),
):
    """Delete an email locally and optionally from the mail server (default true)."""
    rows = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not rows:
        raise HTTPException(404, "Email not found")
    email_row = rows[0]

    # Delete documents from disk and DB
    docs = db.execute("SELECT * FROM documents WHERE email_id = ?", (email_id,))
    for doc in docs:
        try:
            path = Path(doc["stored_path"])
            if path.exists():
                path.unlink()
        except Exception:
            pass
    db.execute("DELETE FROM documents WHERE email_id = ?", (email_id,))

    # Delete email row
    db.execute("DELETE FROM emails WHERE id = ?", (email_id,))

    # Remote delete if requested
    remote_status = "skipped"
    if delete_remote:
        account = next((a for a in settings.email_accounts if a.id == email_row["account_id"]), None)
        if account:
            connector = IMAPConnector(account)
            try:
                connected = await connector.connect()
                if connected:
                    for folder in account.folders:
                        connector.select_folder(folder, readonly=False)
                        msg_ids = connector.search_by_header("Message-ID", email_row["message_id"])
                        if msg_ids:
                            connector.delete_message(msg_ids[0])
                            remote_status = "deleted"
                            break
                if remote_status != "deleted":
                    remote_status = "not_found"
            finally:
                connector.disconnect()
        else:
            remote_status = "account_not_found"

    return {"status": "ok", "remote": remote_status}


@router.post("/fetch/{account_id}")
async def trigger_fetch(account_id: str, scheduler=Depends(get_scheduler)):
    """Manually trigger an email fetch for an account."""
    result = await scheduler.run_now(account_id)
    return {"status": "ok", "job": result}


@router.post("/fetch-all")
async def trigger_fetch_all(scheduler=Depends(get_scheduler)):
    """Trigger email fetch for all enabled accounts."""
    from app.main import app_state
    settings = app_state["settings"]
    results = []
    for account in settings.email_accounts:
        if account.enabled:
            result = await scheduler.run_now(account.id)
            results.append(result)
    return {"status": "ok", "jobs": results}


@router.get("/stats/summary")
async def email_stats(db=Depends(get_db)):
    """Get email ingestion statistics."""
    stats = {
        "total": db.execute("SELECT COUNT(*) as c FROM emails")[0]["c"],
        "pending": db.execute("SELECT COUNT(*) as c FROM emails WHERE status='pending'")[0]["c"],
        "completed": db.execute("SELECT COUNT(*) as c FROM emails WHERE status='completed'")[0]["c"],
        "errors": db.execute("SELECT COUNT(*) as c FROM emails WHERE status='error'")[0]["c"],
        "with_attachments": db.execute("SELECT COUNT(*) as c FROM emails WHERE has_attachments=1")[0]["c"],
    }
    return stats

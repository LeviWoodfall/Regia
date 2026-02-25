"""
Email management routes for Regia.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from app.models import EmailResponse, EmailListResponse

router = APIRouter(prefix="/api/emails", tags=["emails"])


def get_db():
    from app.main import app_state
    return app_state["db"]


def get_scheduler():
    from app.main import app_state
    return app_state["scheduler"]


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

"""
Document management routes for Regia.
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, Response
from typing import Optional

from app.models import DocumentResponse, DocumentListResponse
from app.processing.pdf_handler import render_pdf_page
from app.security import hash_file, verify_file_hash

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_db():
    from app.main import app_state
    return app_state["db"]


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    classification: Optional[str] = None,
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    email_id: Optional[int] = None,
    db=Depends(get_db),
):
    """List documents with pagination and filtering."""
    query = """
        SELECT d.*, e.subject as email_subject, e.sender_name, e.sender_email
        FROM documents d
        LEFT JOIN emails e ON d.email_id = e.id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) as total FROM documents WHERE 1=1"
    params = []
    count_params = []

    if classification:
        query += " AND d.classification = ?"
        count_query += " AND classification = ?"
        params.append(classification)
        count_params.append(classification)
    if category:
        query += " AND d.category = ?"
        count_query += " AND category = ?"
        params.append(category)
        count_params.append(category)
    if source_type:
        query += " AND d.source_type = ?"
        count_query += " AND source_type = ?"
        params.append(source_type)
        count_params.append(source_type)
    if email_id:
        query += " AND d.email_id = ?"
        count_query += " AND email_id = ?"
        params.append(email_id)
        count_params.append(email_id)

    total_rows = db.execute(count_query, tuple(count_params))
    total = total_rows[0]["total"] if total_rows else 0

    offset = (page - 1) * page_size
    query += " ORDER BY d.date_ingested DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    rows = db.execute(query, tuple(params))

    documents = []
    for row in rows:
        documents.append(DocumentResponse(
            id=row["id"],
            email_id=row["email_id"],
            original_filename=row["original_filename"],
            stored_path=row["stored_path"],
            file_size=row["file_size"],
            mime_type=row["mime_type"] or "",
            sha256_hash=row["sha256_hash"],
            hash_verified=bool(row["hash_verified"]),
            source_type=row["source_type"],
            classification=row["classification"] or "",
            category=row["category"] or "",
            ocr_completed=bool(row["ocr_completed"]),
            llm_summary=row["llm_summary"] or "",
            page_count=row["page_count"] or 0,
            date_ingested=row["date_ingested"],
            email_subject=row.get("email_subject") or "",
            sender_name=row.get("sender_name") or "",
            sender_email=row.get("sender_email") or "",
        ))

    return DocumentListResponse(
        documents=documents, total=total, page=page, page_size=page_size
    )


@router.get("/{document_id}")
async def get_document(document_id: int, db=Depends(get_db)):
    """Get document details."""
    rows = db.execute(
        """SELECT d.*, e.subject as email_subject, e.sender_name, e.sender_email
        FROM documents d LEFT JOIN emails e ON d.email_id = e.id
        WHERE d.id = ?""",
        (document_id,),
    )
    if not rows:
        raise HTTPException(404, "Document not found")
    return rows[0]


@router.get("/{document_id}/download")
async def download_document(document_id: int, db=Depends(get_db)):
    """Download a document file."""
    rows = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    if not rows:
        raise HTTPException(404, "Document not found")

    doc = rows[0]
    filepath = doc["stored_path"]

    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found on disk")

    return FileResponse(
        filepath,
        filename=doc["original_filename"],
        media_type=doc["mime_type"] or "application/octet-stream",
    )


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: int,
    page: int = Query(0, ge=0),
    dpi: int = Query(150, ge=72, le=300),
    db=Depends(get_db),
):
    """Get a PNG preview of a document page."""
    rows = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    if not rows:
        raise HTTPException(404, "Document not found")

    doc = rows[0]
    filepath = doc["stored_path"]

    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found on disk")

    png_bytes = render_pdf_page(filepath, page_number=page, dpi=dpi)
    if not png_bytes:
        raise HTTPException(404, "Could not render page")

    return Response(content=png_bytes, media_type="image/png")


@router.get("/{document_id}/verify")
async def verify_document(document_id: int, db=Depends(get_db)):
    """Verify document integrity by checking its hash."""
    rows = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    if not rows:
        raise HTTPException(404, "Document not found")

    doc = rows[0]
    filepath = doc["stored_path"]

    if not os.path.exists(filepath):
        return {"verified": False, "error": "File not found on disk"}

    current_hash = hash_file(filepath)
    verified = current_hash == doc["sha256_hash"]

    # Update verification status
    db.execute(
        "UPDATE documents SET hash_verified = ? WHERE id = ?",
        (1 if verified else 0, document_id),
    )

    return {
        "verified": verified,
        "stored_hash": doc["sha256_hash"],
        "current_hash": current_hash,
    }


@router.get("/{document_id}/text")
async def get_document_text(document_id: int, db=Depends(get_db)):
    """Get the OCR/extracted text of a document."""
    rows = db.execute(
        "SELECT ocr_text, llm_summary FROM documents WHERE id = ?",
        (document_id,),
    )
    if not rows:
        raise HTTPException(404, "Document not found")

    return {
        "ocr_text": rows[0]["ocr_text"] or "",
        "llm_summary": rows[0]["llm_summary"] or "",
    }


@router.get("/stats/summary")
async def document_stats(db=Depends(get_db)):
    """Get document statistics."""
    stats = {
        "total": db.execute("SELECT COUNT(*) as c FROM documents")[0]["c"],
        "total_size": db.execute("SELECT COALESCE(SUM(file_size), 0) as s FROM documents")[0]["s"],
        "ocr_completed": db.execute("SELECT COUNT(*) as c FROM documents WHERE ocr_completed=1")[0]["c"],
        "classifications": db.execute(
            "SELECT classification, COUNT(*) as count FROM documents WHERE classification != '' GROUP BY classification ORDER BY count DESC"
        ),
        "categories": db.execute(
            "SELECT category, COUNT(*) as count FROM documents WHERE category != '' GROUP BY category ORDER BY count DESC"
        ),
    }
    return stats

"""
File system browser routes for Regia.
Provides a clean file system view of the document storage directory.
"""

import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List

from app.models import FileNode, FileBrowserResponse

router = APIRouter(prefix="/api/files", tags=["files"])


def get_settings():
    from app.main import app_state
    return app_state["settings"]


def get_db():
    from app.main import app_state
    return app_state["db"]


@router.get("/browse")
async def browse(
    path: str = Query("", description="Relative path within the storage directory"),
    settings=Depends(get_settings),
    db=Depends(get_db),
):
    """Browse the document storage directory."""
    base = Path(settings.storage.base_dir)
    base.mkdir(parents=True, exist_ok=True)

    target = base / path if path else base

    # Security: ensure path stays within base directory
    try:
        target = target.resolve()
        base_resolved = base.resolve()
        if not str(target).startswith(str(base_resolved)):
            raise HTTPException(403, "Access denied: path outside storage directory")
    except Exception:
        raise HTTPException(400, "Invalid path")

    if not target.exists():
        raise HTTPException(404, "Path not found")

    if target.is_file():
        # Return file info
        stat = target.stat()
        # Try to find document in DB
        doc_rows = db.execute(
            "SELECT id, mime_type, classification, category FROM documents WHERE stored_path = ?",
            (str(target),),
        )
        doc_info = doc_rows[0] if doc_rows else {}

        return {
            "type": "file",
            "name": target.name,
            "path": str(target.relative_to(base_resolved)),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "document_id": doc_info.get("id"),
            "mime_type": doc_info.get("mime_type", ""),
            "classification": doc_info.get("classification", ""),
            "category": doc_info.get("category", ""),
        }

    # Directory listing
    nodes = []
    total_files = 0
    total_size = 0

    try:
        entries = sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except PermissionError:
        raise HTTPException(403, "Permission denied")

    for entry in entries:
        try:
            stat = entry.stat()
            rel_path = str(entry.relative_to(base_resolved))

            if entry.is_dir():
                # Count children
                child_count = sum(1 for _ in entry.iterdir()) if entry.exists() else 0
                nodes.append(FileNode(
                    name=entry.name,
                    path=rel_path,
                    type="directory",
                    size=child_count,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                ))
            else:
                total_files += 1
                total_size += stat.st_size

                # Look up document info
                doc_rows = db.execute(
                    "SELECT id, mime_type FROM documents WHERE stored_path = ?",
                    (str(entry),),
                )
                doc_info = doc_rows[0] if doc_rows else {}

                nodes.append(FileNode(
                    name=entry.name,
                    path=rel_path,
                    type="file",
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    document_id=doc_info.get("id"),
                    mime_type=doc_info.get("mime_type", ""),
                ))
        except (PermissionError, OSError):
            continue

    return FileBrowserResponse(
        root=str(target.relative_to(base_resolved)) if target != base_resolved else "",
        nodes=nodes,
        total_files=total_files,
        total_size=total_size,
    )


@router.get("/tree")
async def directory_tree(
    max_depth: int = Query(3, ge=1, le=10),
    settings=Depends(get_settings),
):
    """Get a directory tree of the storage directory."""
    base = Path(settings.storage.base_dir)
    base.mkdir(parents=True, exist_ok=True)

    def build_tree(path: Path, depth: int = 0) -> dict:
        node = {
            "name": path.name or "Documents",
            "type": "directory",
            "children": [],
        }
        if depth >= max_depth:
            return node

        try:
            for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                if entry.is_dir():
                    node["children"].append(build_tree(entry, depth + 1))
                else:
                    node["children"].append({
                        "name": entry.name,
                        "type": "file",
                        "size": entry.stat().st_size,
                    })
        except (PermissionError, OSError):
            pass

        return node

    tree = build_tree(base)
    return tree

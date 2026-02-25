"""
Search routes for Regia.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.models import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


def get_search_engine():
    from app.main import app_state
    return app_state["search_engine"]


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest, engine=Depends(get_search_engine)):
    """Perform a full-text search across emails and documents."""
    result = engine.search(
        query=request.query,
        scope=request.scope,
        filters=request.filters,
        page=request.page,
        page_size=request.page_size,
    )
    return SearchResponse(**result)


@router.get("/suggest")
async def suggest(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    engine=Depends(get_search_engine),
):
    """Get search suggestions for autocomplete."""
    suggestions = engine.get_suggestions(q, limit)
    return {"suggestions": suggestions}


@router.get("/classifications")
async def get_classifications(engine=Depends(get_search_engine)):
    """Get all document classifications with counts."""
    return {"classifications": engine.get_classifications()}


@router.get("/categories")
async def get_categories(engine=Depends(get_search_engine)):
    """Get all document categories with counts."""
    return {"categories": engine.get_categories()}

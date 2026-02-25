"""
Reggie AI agent routes for Regia.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


def get_agent():
    from app.main import app_state
    return app_state["agent"]


@router.get("/status")
async def agent_status(agent=Depends(get_agent)):
    """Check if Reggie is available."""
    available = await agent.is_available()
    memory_stats = agent.learning.get_memory_stats()
    knowledge_stats = agent.learning.get_knowledge_stats()
    return {
        "available": available,
        "name": "Reggie",
        "model": agent.config.model_name,
        "memory_stats": memory_stats,
        "knowledge_stats": knowledge_stats,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, agent=Depends(get_agent)):
    """Send a message to Reggie and get a response."""
    result = await agent.chat(
        message=request.message,
        session_id=request.session_id,
        context=request.context,
    )
    return ChatResponse(**result)


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session."""
    from app.main import app_state
    db = app_state["db"]
    rows = db.execute(
        "SELECT role, content, created_at FROM chat_history WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    )
    return {"session_id": session_id, "messages": rows}


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history for a session."""
    from app.main import app_state
    db = app_state["db"]
    db.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    return {"status": "ok"}


# === Memory Management ===

@router.get("/memory")
async def list_memories(agent=Depends(get_agent)):
    """List all of Reggie's stored memories."""
    memories = agent.learning.get_all_memories(limit=100)
    stats = agent.learning.get_memory_stats()
    return {"memories": memories, "stats": stats}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int, agent=Depends(get_agent)):
    """Delete a specific memory."""
    success = agent.learning.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "ok"}


@router.delete("/memory")
async def clear_all_memories():
    """Clear all of Reggie's memories."""
    from app.main import app_state
    db = app_state["db"]
    db.execute("DELETE FROM reggie_memory")
    return {"status": "ok", "message": "All memories cleared"}


# === Knowledge Base ===

@router.get("/knowledge")
async def list_knowledge(agent=Depends(get_agent)):
    """Get Reggie's knowledge base stats and recent entries."""
    stats = agent.learning.get_knowledge_stats()
    from app.main import app_state
    db = app_state["db"]
    recent = db.execute(
        """SELECT k.*, d.original_filename, e.subject as email_subject
           FROM reggie_knowledge k
           LEFT JOIN documents d ON k.document_id = d.id
           LEFT JOIN emails e ON k.email_id = e.id
           ORDER BY k.created_at DESC LIMIT 50"""
    )
    return {"knowledge": recent, "stats": stats}


@router.delete("/knowledge")
async def clear_all_knowledge():
    """Clear all of Reggie's knowledge base."""
    from app.main import app_state
    db = app_state["db"]
    db.execute("DELETE FROM reggie_knowledge")
    return {"status": "ok", "message": "All knowledge cleared"}

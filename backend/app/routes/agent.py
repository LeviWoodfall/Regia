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
    return {
        "available": available,
        "name": "Reggie",
        "model": agent.config.model_name,
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

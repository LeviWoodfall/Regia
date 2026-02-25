"""
Cloud storage API routes for Regia.
Handles OneDrive and Google Drive connections, OAuth2 flows, and sync operations.
"""

import secrets
import logging
from fastapi import APIRouter, HTTPException, Request, Query

from app.models import (
    CloudStorageConnect, CloudStorageConnection, CloudSyncRequest,
    OAuth2StartRequest, OAuth2StartResponse,
)
from app.cloud_storage.oauth2 import start_oauth2_flow, exchange_oauth2_code
from app.cloud_storage.providers import CLOUD_OAUTH2_PROVIDERS, EMAIL_OAUTH2_PROVIDERS

logger = logging.getLogger("regia.routes.cloud")

router = APIRouter(prefix="/api/cloud-storage", tags=["cloud-storage"])


def _get_state(request: Request):
    from app.main import app_state
    return app_state


@router.get("/providers")
async def list_providers():
    """List available cloud storage providers."""
    providers = []
    for key, val in CLOUD_OAUTH2_PROVIDERS.items():
        providers.append({
            "id": key,
            "display_name": val["display_name"],
            "connect_label": val["connect_label"],
        })
    return {"providers": providers}


@router.get("/email-providers")
async def list_email_providers():
    """List available email OAuth2 providers (for Connect with buttons)."""
    providers = []
    for key, val in EMAIL_OAUTH2_PROVIDERS.items():
        providers.append({
            "id": key,
            "display_name": val["display_name"],
            "connect_label": val["connect_label"],
            "imap_server": val["imap_server"],
            "imap_port": val["imap_port"],
        })
    return {"providers": providers}


@router.get("/connections")
async def list_connections(request: Request):
    """List all cloud storage connections."""
    state = _get_state(request)
    db = state["db"]
    connections = db.execute(
        "SELECT * FROM cloud_storage_connections ORDER BY created_at DESC"
    )
    return {"connections": connections}


@router.post("/connect")
async def create_connection(data: CloudStorageConnect, request: Request):
    """Register a new cloud storage connection (before OAuth2 flow)."""
    state = _get_state(request)
    db = state["db"]

    if data.provider not in CLOUD_OAUTH2_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {data.provider}")

    provider_info = CLOUD_OAUTH2_PROVIDERS[data.provider]
    conn_id = secrets.token_hex(8)

    db.execute_insert(
        """INSERT INTO cloud_storage_connections (id, provider, display_name, sync_folder)
           VALUES (?, ?, ?, 'Regia')""",
        (conn_id, data.provider, provider_info["display_name"]),
    )

    return {"connection_id": conn_id, "provider": data.provider}


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str, request: Request):
    """Remove a cloud storage connection."""
    state = _get_state(request)
    db = state["db"]
    db.execute("DELETE FROM cloud_sync_log WHERE connection_id = ?", (connection_id,))
    db.execute("DELETE FROM cloud_storage_connections WHERE id = ?", (connection_id,))
    return {"message": "Connection removed"}


@router.post("/oauth2/start", response_model=OAuth2StartResponse)
async def start_oauth2(data: OAuth2StartRequest):
    """Start an OAuth2 authorization flow for cloud storage or email."""
    try:
        redirect_uri = "http://localhost:8420/api/oauth2/callback"
        result = start_oauth2_flow(
            flow_type=data.flow_type,
            provider=data.provider,
            client_id=data.client_id,
            client_secret=data.client_secret,
            redirect_uri=redirect_uri,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sync/{connection_id}/status")
async def get_sync_status(connection_id: str, request: Request):
    """Get sync status for a connection."""
    state = _get_state(request)
    db = state["db"]

    conn = db.execute(
        "SELECT * FROM cloud_storage_connections WHERE id = ?", (connection_id,)
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    total_synced = db.execute(
        "SELECT COUNT(*) as c FROM cloud_sync_log WHERE connection_id = ? AND status = 'synced'",
        (connection_id,),
    )[0]["c"]

    total_errors = db.execute(
        "SELECT COUNT(*) as c FROM cloud_sync_log WHERE connection_id = ? AND status = 'error'",
        (connection_id,),
    )[0]["c"]

    total_docs = db.execute("SELECT COUNT(*) as c FROM documents")[0]["c"]

    return {
        "connection": conn[0],
        "total_synced": total_synced,
        "total_errors": total_errors,
        "total_documents": total_docs,
        "pending": total_docs - total_synced,
    }


# === OAuth2 Callback (shared for both cloud storage and email) ===

from fastapi import APIRouter as _AR

oauth_router = APIRouter(prefix="/api/oauth2", tags=["oauth2"])


@oauth_router.get("/callback")
async def oauth2_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
):
    """OAuth2 callback handler. Exchanges code for tokens and stores them."""
    try:
        tokens = await exchange_oauth2_code(code, state)

        app_state = _get_state(request)
        db = app_state["db"]

        if tokens["flow_type"] == "cloud_storage":
            # Store tokens encrypted and mark connection as connected
            from app.security import credential_manager
            cred_key = f"cloud_{tokens['provider']}_{state[:8]}"
            credential_manager.store_credential(cred_key, {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            })

            # Find the most recent unconnected connection for this provider
            conns = db.execute(
                """SELECT id FROM cloud_storage_connections
                   WHERE provider = ? AND connected = 0
                   ORDER BY created_at DESC LIMIT 1""",
                (tokens["provider"],),
            )
            if conns:
                db.execute(
                    "UPDATE cloud_storage_connections SET connected = 1 WHERE id = ?",
                    (conns[0]["id"],),
                )

        elif tokens["flow_type"] == "email":
            # Store email OAuth tokens
            from app.security import credential_manager
            cred_key = f"email_oauth_{tokens['provider']}_{state[:8]}"
            credential_manager.store_credential(cred_key, {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            })

        # Return a nice HTML page that auto-closes
        html = """
        <!DOCTYPE html>
        <html><head><title>Regia - Connected</title>
        <style>
            body { font-family: system-ui; display: flex; align-items: center;
                   justify-content: center; height: 100vh; margin: 0;
                   background: #fdf8f3; color: #3a1b13; }
            .card { text-align: center; padding: 2rem; }
            h2 { color: #dd5b16; }
        </style></head>
        <body><div class="card">
            <h2>Connected!</h2>
            <p>You can close this window and return to Regia.</p>
            <script>setTimeout(() => window.close(), 2000);</script>
        </div></body></html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 error: {str(e)}")

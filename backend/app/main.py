"""
Regia - Intelligent Email Ingestion & Document Management System
Main FastAPI application entry point.
"""

import logging
import socket
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app import __version__, __app_name__, __agent_name__
from app.config import load_config, save_config, AppSettings, APP_DATA_DIR, DEFAULT_LOG_DIR
from app.database import Database
from app.search.engine import SearchEngine
from app.llm.agent import ReggieAgent
from app.llm.ollama_manager import OllamaManager
from app.scheduler.jobs import EmailScheduler
from app.auth import AuthManager
from app.cloud_storage.sync import CloudSyncEngine

# === Logging Setup ===

def setup_logging(settings: AppSettings):
    """Configure application logging."""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "regia.log", encoding="utf-8"),
        ],
    )

    # Quiet noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


logger = logging.getLogger("regia")

# === Global Application State ===
# Shared across routes via dependency injection
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # --- Startup ---
    settings = load_config()
    setup_logging(settings)
    logger.info(f"Starting {__app_name__} v{__version__}")

    # Ensure directories exist
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    Path(settings.storage.base_dir).mkdir(parents=True, exist_ok=True)

    # Initialize database
    db = Database(settings.db_path)
    logger.info(f"Database initialized at {settings.db_path}")

    # Auto-start Ollama if configured
    ollama_manager = OllamaManager(
        base_url=settings.llm.ollama_base_url,
        model_name=settings.llm.model_name,
    )
    if settings.auto_start_ollama:
        if not await ollama_manager.is_running():
            logger.info("Starting Ollama AI engine...")
            ollama_manager.start()
        else:
            logger.info("Ollama AI engine already running")
        # Ensure model is available
        await ollama_manager.ensure_model()

    # Initialize search engine
    search_engine = SearchEngine(db, settings.search)

    # Initialize Reggie agent
    agent = ReggieAgent(db, settings.llm)

    # Initialize auth manager
    auth_manager = AuthManager(db, settings.auth.session_timeout_minutes)

    # Initialize cloud sync engine
    cloud_sync = CloudSyncEngine(db)

    # Initialize scheduler
    scheduler = EmailScheduler(db, settings)
    if settings.scheduler.enabled:
        scheduler.start()
        logger.info("Email scheduler started")

    # Save config (creates default if first run)
    save_config(settings)

    # Populate app state
    app_state["settings"] = settings
    app_state["db"] = db
    app_state["search_engine"] = search_engine
    app_state["agent"] = agent
    app_state["auth_manager"] = auth_manager
    app_state["cloud_sync"] = cloud_sync
    app_state["ollama_manager"] = ollama_manager
    app_state["scheduler"] = scheduler

    # Mount built frontend for serving
    dist = _find_frontend_dist(settings)
    if dist:
        logger.info(f"Serving frontend from {dist}")
        if (dist / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="frontend-assets")
        app_state["frontend_dist"] = dist
    else:
        logger.warning("Frontend dist not found — run 'npm run build' in frontend/")

    logger.info(f"{__app_name__} is ready at http://{settings.host}:{settings.port}")
    logger.info(f"LAN access: http://{lan_ip}:{settings.port}")

    yield

    # --- Shutdown ---
    logger.info(f"Shutting down {__app_name__}...")
    scheduler.stop()
    if ollama_manager.managed:
        ollama_manager.stop()
    logger.info("Shutdown complete")


# === FastAPI App ===

app = FastAPI(
    title=__app_name__,
    description="Intelligent Email Ingestion & Document Management System",
    version=__version__,
    lifespan=lifespan,
)

# CORS — allow frontend dev server + any LAN client
def _get_lan_ip() -> str:
    """Get the machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

lan_ip = _get_lan_ip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173",
        "http://localhost:8420", "http://127.0.0.1:8420",
        f"http://{lan_ip}:5173", f"http://{lan_ip}:8420",
        "tauri://localhost",  # Tauri desktop app
    ],
    allow_origin_regex=r"http://192\.168\..*",  # Allow any 192.168.x.x LAN client
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Register Routes ===

from app.routes import settings, emails, documents, search, agent, files  # noqa: E402
from app.routes import auth as auth_routes  # noqa: E402
from app.routes import cloud_storage as cloud_routes  # noqa: E402

app.include_router(auth_routes.router)
app.include_router(settings.router)
app.include_router(emails.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(agent.router)
app.include_router(files.router)
app.include_router(cloud_routes.router)
app.include_router(cloud_routes.oauth_router)


# === Serve Built Frontend (fixes 404 on /) ===

def _find_frontend_dist(settings=None) -> Path | None:
    """Auto-detect the built frontend dist directory."""
    if settings and settings.frontend_dist_dir:
        p = Path(settings.frontend_dist_dir)
        if p.exists() and (p / "index.html").exists():
            return p
    # Auto-detect: look relative to backend directory
    backend_dir = Path(__file__).resolve().parent.parent
    candidates = [
        backend_dir.parent / "frontend" / "dist",
        backend_dir / "frontend" / "dist",
        Path.cwd().parent / "frontend" / "dist",
        Path.cwd() / ".." / "frontend" / "dist",
    ]
    for c in candidates:
        c = c.resolve()
        if c.exists() and (c / "index.html").exists():
            return c
    return None


# === Network Discovery Endpoint ===

@app.get("/api/network/info")
async def network_info():
    """Return server network info for LAN client discovery."""
    settings = app_state["settings"]
    return {
        "app": __app_name__,
        "version": __version__,
        "lan_ip": lan_ip,
        "port": settings.port,
        "url": f"http://{lan_ip}:{settings.port}",
    }


# === Root Routes ===

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    ollama_mgr = app_state.get("ollama_manager")
    return {
        "status": "ok",
        "app": __app_name__,
        "version": __version__,
        "agent": __agent_name__,
        "ollama_running": await ollama_mgr.is_running() if ollama_mgr else False,
    }


@app.get("/api/ui/preferences")
async def get_ui_preferences():
    """Get UI preferences (theme, accent color)."""
    settings = app_state["settings"]
    return {
        "theme": settings.ui.theme,
        "accent_color": settings.ui.accent_color,
        "sidebar_collapsed": settings.ui.sidebar_collapsed,
    }


@app.put("/api/ui/preferences")
async def update_ui_preferences(prefs: dict):
    """Update UI preferences."""
    settings = app_state["settings"]
    if "theme" in prefs:
        settings.ui.theme = prefs["theme"]
    if "accent_color" in prefs:
        settings.ui.accent_color = prefs["accent_color"]
    if "sidebar_collapsed" in prefs:
        settings.ui.sidebar_collapsed = prefs["sidebar_collapsed"]
    save_config(settings)
    return {"message": "Preferences saved", "theme": settings.ui.theme}


@app.get("/api/dashboard")
async def dashboard():
    """Get dashboard statistics."""
    db = app_state["db"]
    settings = app_state["settings"]

    total_emails = db.execute("SELECT COUNT(*) as c FROM emails")[0]["c"]
    total_docs = db.execute("SELECT COUNT(*) as c FROM documents")[0]["c"]
    total_size = db.execute("SELECT COALESCE(SUM(file_size), 0) as s FROM documents")[0]["s"]
    pending = db.execute("SELECT COUNT(*) as c FROM emails WHERE status='pending'")[0]["c"]
    active_accounts = len([a for a in settings.email_accounts if a.enabled])

    last_sync_rows = db.execute(
        "SELECT MAX(last_sync_at) as last FROM email_accounts"
    )
    last_sync = last_sync_rows[0]["last"] if last_sync_rows else None

    recent_emails = db.execute(
        "SELECT * FROM emails ORDER BY date_ingested DESC LIMIT 5"
    )
    recent_docs = db.execute(
        """SELECT d.*, e.subject as email_subject, e.sender_name
        FROM documents d LEFT JOIN emails e ON d.email_id = e.id
        ORDER BY d.date_ingested DESC LIMIT 5"""
    )

    return {
        "total_emails": total_emails,
        "total_documents": total_docs,
        "total_storage_bytes": total_size,
        "accounts_active": active_accounts,
        "last_sync": last_sync,
        "pending_processing": pending,
        "recent_emails": recent_emails,
        "recent_documents": recent_docs,
    }


@app.get("/api/logs")
async def get_logs(
    page: int = 1,
    page_size: int = 50,
    status: str = None,
):
    """Get ingestion logs."""
    db = app_state["db"]
    query = "SELECT * FROM ingestion_logs WHERE 1=1"
    count_query = "SELECT COUNT(*) as total FROM ingestion_logs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)

    total = db.execute(count_query, tuple(params))[0]["total"]

    offset = (page - 1) * page_size
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    logs = db.execute(query, tuple(params))

    return {"logs": logs, "total": total, "page": page, "page_size": page_size}


# === SPA Catch-All (must be last) ===

@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    """Serve the frontend SPA for any non-API route."""
    # Skip API routes (already handled above)
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    dist = app_state.get("frontend_dist")
    if not dist:
        return JSONResponse(
            {"detail": "Frontend not built. Run 'npm run build' in frontend/"},
            status_code=503,
        )

    # Try to serve the exact file first (e.g., favicon.ico, regia.svg)
    file_path = dist / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))

    # Otherwise serve index.html for SPA client-side routing
    index = dist / "index.html"
    if index.exists():
        return FileResponse(str(index))

    return JSONResponse({"detail": "Not Found"}, status_code=404)

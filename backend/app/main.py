"""
Regia - Intelligent Email Ingestion & Document Management System
Main FastAPI application entry point.
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__, __app_name__, __agent_name__
from app.config import load_config, save_config, AppSettings, APP_DATA_DIR, DEFAULT_LOG_DIR
from app.database import Database
from app.search.engine import SearchEngine
from app.llm.agent import ReggieAgent
from app.scheduler.jobs import EmailScheduler

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

    # Initialize search engine
    search_engine = SearchEngine(db, settings.search)

    # Initialize Reggie agent
    agent = ReggieAgent(db, settings.llm)

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
    app_state["scheduler"] = scheduler

    logger.info(f"{__app_name__} is ready at http://{settings.host}:{settings.port}")

    yield

    # --- Shutdown ---
    logger.info(f"Shutting down {__app_name__}...")
    scheduler.stop()
    logger.info("Shutdown complete")


# === FastAPI App ===

app = FastAPI(
    title=__app_name__,
    description="Intelligent Email Ingestion & Document Management System",
    version=__version__,
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Register Routes ===

from app.routes import settings, emails, documents, search, agent, files  # noqa: E402

app.include_router(settings.router)
app.include_router(emails.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(agent.router)
app.include_router(files.router)


# === Root Routes ===

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": __app_name__,
        "version": __version__,
        "agent": __agent_name__,
    }


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

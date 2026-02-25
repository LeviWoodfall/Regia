"""
Configuration management for Regia.
Handles application settings, paths, and encrypted credential storage.
"""

import os
import json
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# === Default Paths ===
def get_app_data_dir() -> Path:
    """Get platform-appropriate application data directory."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.name == "posix":
        if "ANDROID_ROOT" in os.environ:
            base = Path.home() / ".regia"
        elif os.uname().sysname == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    else:
        base = Path.home()
    return base / "Regia"


APP_DATA_DIR = get_app_data_dir()
DEFAULT_STORAGE_DIR = APP_DATA_DIR / "documents"
DEFAULT_DB_PATH = APP_DATA_DIR / "regia.db"
DEFAULT_LOG_DIR = APP_DATA_DIR / "logs"
DEFAULT_CONFIG_PATH = APP_DATA_DIR / "config.json"
CREDENTIALS_PATH = APP_DATA_DIR / "credentials.enc"


# === Pydantic Settings Models ===

class EmailAccountConfig(BaseModel):
    """Configuration for a single email account."""
    id: str = Field(default_factory=lambda: secrets.token_hex(8))
    name: str = ""
    email: str
    provider: str = "imap"  # gmail, outlook, imap
    imap_server: str = ""
    imap_port: int = 993
    use_ssl: bool = True
    auth_method: str = "oauth2"  # oauth2, app_password
    # OAuth2 fields (tokens stored encrypted separately)
    client_id: str = ""
    client_secret: str = ""
    # Polling config
    enabled: bool = True
    poll_interval_minutes: int = 15
    folders: List[str] = Field(default_factory=lambda: ["INBOX"])
    # Post-processing
    mark_as_read: bool = True
    move_to_folder: str = ""  # e.g., "Processed" - empty = leave in place
    max_attachment_size_mb: int = 50
    download_invoice_links: bool = True


class LLMConfig(BaseModel):
    """Configuration for the lightweight LLM."""
    provider: str = "ollama"  # ollama, llamacpp
    model_name: str = "qwen2.5:0.5b"  # Ultra-lightweight default
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 512
    timeout_seconds: int = 30
    # Fallback to rule-based if LLM unavailable
    fallback_to_rules: bool = True


class OCRConfig(BaseModel):
    """Configuration for OCR processing."""
    enabled: bool = True
    engine: str = "tesseract"  # tesseract
    language: str = "eng"
    dpi: int = 300


class SearchConfig(BaseModel):
    """Configuration for the search engine."""
    enable_fts: bool = True
    enable_ocr_indexing: bool = True
    max_results: int = 50
    snippet_length: int = 200


class StorageConfig(BaseModel):
    """Configuration for document storage."""
    base_dir: str = str(DEFAULT_STORAGE_DIR)
    # Naming: {email}/{date}/{sender}/{subject}/filename
    folder_template: str = "{email}/{date}/{sender}/{subject}"
    date_format: str = "%Y-%m-%d"
    sanitize_names: bool = True
    max_filename_length: int = 100
    verify_hash: bool = True
    hash_algorithm: str = "sha256"


class SchedulerConfig(BaseModel):
    """Configuration for the email polling scheduler."""
    enabled: bool = True
    default_interval_minutes: int = 15
    max_concurrent_jobs: int = 2
    retry_on_failure: bool = True
    max_retries: int = 3


class SecurityConfig(BaseModel):
    """Security configuration."""
    encryption_enabled: bool = True
    # Master key derived from user password via PBKDF2
    session_timeout_minutes: int = 60
    # One-way data flow enforcement
    allow_write_back: bool = False  # NEVER allow writing back to email
    allow_outbound_connections: bool = True  # For invoice link downloads


class AppSettings(BaseSettings):
    """Main application settings."""
    app_name: str = "Regia"
    agent_name: str = "Reggie"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8420
    db_path: str = str(DEFAULT_DB_PATH)
    log_dir: str = str(DEFAULT_LOG_DIR)
    log_level: str = "INFO"

    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    email_accounts: List[EmailAccountConfig] = Field(default_factory=list)

    class Config:
        env_prefix = "REGIA_"
        env_file = ".env"


def load_config() -> AppSettings:
    """Load configuration from file, falling back to defaults."""
    if DEFAULT_CONFIG_PATH.exists():
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                data = json.load(f)
            return AppSettings(**data)
        except Exception:
            pass
    return AppSettings()


def save_config(settings: AppSettings) -> None:
    """Save configuration to file."""
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_CONFIG_PATH, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)

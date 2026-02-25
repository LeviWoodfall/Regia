"""
Pydantic models for Regia API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# === Email Models ===

class EmailAccountCreate(BaseModel):
    name: str = ""
    email: str
    provider: str = "imap"
    imap_server: str = ""
    imap_port: int = 993
    use_ssl: bool = True
    auth_method: str = "oauth2"
    client_id: str = ""
    client_secret: str = ""
    poll_interval_minutes: int = 15
    folders: List[str] = Field(default_factory=lambda: ["INBOX"])
    mark_as_read: bool = True
    move_to_folder: str = ""
    max_attachment_size_mb: int = 50
    download_invoice_links: bool = True


class EmailAccountResponse(BaseModel):
    id: str
    name: str
    email: str
    provider: str
    enabled: bool
    last_sync_at: Optional[str] = None
    created_at: str
    has_credentials: bool = False


class EmailResponse(BaseModel):
    id: int
    account_id: str
    message_id: str
    subject: str
    sender_email: str
    sender_name: str
    date_sent: Optional[str]
    date_ingested: str
    has_attachments: bool
    has_invoice_links: bool
    status: str
    classification: str
    llm_summary: str
    document_count: int = 0


class EmailListResponse(BaseModel):
    emails: List[EmailResponse]
    total: int
    page: int
    page_size: int


# === Document Models ===

class DocumentResponse(BaseModel):
    id: int
    email_id: Optional[int]
    original_filename: str
    stored_path: str
    file_size: int
    mime_type: str
    sha256_hash: str
    hash_verified: bool
    source_type: str
    classification: str
    category: str
    ocr_completed: bool
    llm_summary: str
    page_count: int
    date_ingested: str
    # Related email info
    email_subject: str = ""
    sender_name: str = ""
    sender_email: str = ""


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# === Search Models ===

class SearchRequest(BaseModel):
    query: str
    scope: str = "all"  # all, documents, emails
    filters: Dict[str, Any] = Field(default_factory=dict)
    page: int = 1
    page_size: int = 20


class SearchResult(BaseModel):
    type: str  # email, document
    id: int
    title: str
    snippet: str
    relevance_score: float
    date: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    took_ms: float


# === Agent Models ===

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    message: str
    session_id: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# === Settings Models ===

class MasterPasswordSetup(BaseModel):
    password: str


class MasterPasswordUnlock(BaseModel):
    password: str


class OAuthCredentials(BaseModel):
    account_id: str
    app_password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[str] = None


# === File Browser Models ===

class FileNode(BaseModel):
    name: str
    path: str
    type: str  # file, directory
    size: int = 0
    modified: Optional[str] = None
    children: Optional[List["FileNode"]] = None
    document_id: Optional[int] = None
    mime_type: str = ""


class FileBrowserResponse(BaseModel):
    root: str
    nodes: List[FileNode]
    total_files: int
    total_size: int


# === Dashboard Models ===

class DashboardStats(BaseModel):
    total_emails: int = 0
    total_documents: int = 0
    total_storage_bytes: int = 0
    accounts_active: int = 0
    last_sync: Optional[str] = None
    pending_processing: int = 0
    recent_emails: List[EmailResponse] = Field(default_factory=list)
    recent_documents: List[DocumentResponse] = Field(default_factory=list)


# === Log Models ===

class LogEntry(BaseModel):
    id: int
    account_id: Optional[str]
    action: str
    status: str
    message: str
    created_at: str


class LogListResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int


# === Auth Models ===

class UserSetup(BaseModel):
    username: str
    password: str
    email: str = ""
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    display_name: str
    expires_at: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# === Cloud Storage Models ===

class CloudStorageConnect(BaseModel):
    provider: str  # onedrive, google_drive
    client_id: str = ""
    client_secret: str = ""


class CloudStorageConnection(BaseModel):
    id: str
    provider: str
    display_name: str
    connected: bool
    last_sync_at: Optional[str]
    sync_folder: str
    total_synced: int


class CloudSyncRequest(BaseModel):
    connection_id: str


# === OAuth2 Models ===

class OAuth2StartRequest(BaseModel):
    flow_type: str  # cloud_storage, email
    provider: str  # onedrive, google_drive, gmail, outlook
    client_id: str = ""
    client_secret: str = ""


class OAuth2StartResponse(BaseModel):
    url: str
    state: str


# === UI Preferences ===

class UIPreferences(BaseModel):
    theme: str = "light"  # light, dark
    accent_color: str = "sunset"
    sidebar_collapsed: bool = False

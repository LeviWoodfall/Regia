# Regia

**Intelligent Email Ingestion & Document Management System**

Regia automatically ingests emails from any provider (Gmail, Outlook, custom IMAP), extracts PDF attachments and invoice links, classifies them using a lightweight local LLM, and organizes everything into a structured, searchable document archive — all with a warm, modern UI.

The built-in AI assistant **Reggie** can search across your entire document archive and answer questions conversationally.

---

## Features

### Core
- **Multi-Provider Email Ingestion** — Gmail, Outlook, any IMAP server with OAuth2 or app password authentication
- **"Connect with Microsoft/Google" OAuth2** — Secure one-click sign-in for email and cloud storage
- **Cloud Storage Sync** — Automatically sync documents to OneDrive or Google Drive
- **One-Way Data Flow** — Emails are pulled read-only; no write-back access to your accounts
- **PDF Processing** — Extract text, OCR scanned documents, compute SHA-256 integrity hashes
- **Invoice Link Detection** — Automatically detects and downloads invoices from email links
- **Structured Storage** — Documents stored as `{email}/{date}/{sender}/{subject}/filename`
- **Full-Text Search** — SQLite FTS5 across emails, documents, OCR text, and AI summaries
- **Configurable Scheduler** — Control polling frequency, post-processing, and retry behavior
- **Detailed Logging** — Full audit trail with hash verification for every document

### AI
- **Lightweight LLM Classification** — Uses Ollama with ultra-light models (Qwen2.5:0.5b, TinyLlama) with rule-based fallback
- **Fully Offline AI** — Reggie is trained on your data only, never connects to the internet
- **Auto-Start AI Engine** — Ollama starts automatically with the server, model pulled on first run
- **Reggie AI Agent** — Conversational search assistant using RAG over your document archive

### Security & Auth
- **User Authentication** — Username/password login with PBKDF2-hashed passwords and session tokens
- **Forgot Password** — Email-based password reset via SMTP (auto-derived from configured email providers)
- **Login-First Flow** — Login page shown by default; account creation only available when no users exist
- **Encrypted Credentials** — Master password with PBKDF2 key derivation and Fernet encryption (480,000 iterations)

### Desktop & Network
- **Standalone Desktop App** — Runs as a native desktop app via Tauri v2 (Windows, Linux, macOS)
- **Network Discoverable** — Backend binds to `0.0.0.0` with CORS for LAN access; `/api/network/info` endpoint
- **Private Cloud** — Mobile/LAN clients connect to the main server instance via configurable API URL
- **Dark Mode** — Warm, darker version of the light theme, soft on the eyes in dark rooms
- **Cross-Platform** — Windows, Linux, macOS (desktop); Android, iOS (via browser/PWA)
- **One-Click Installer** — Auto-installs all prerequisites (Python, Node.js, Ollama)
- **Self-Contained** — SQLite database, fully self-hosted, no external services required

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLite (FTS5, WAL mode) |
| Frontend | React 19, TypeScript, TailwindCSS v4, Vite |
| Desktop | Tauri v2 (Rust) — native app with shell, http, process, os, notification plugins |
| LLM | Ollama (local only), Qwen2.5:0.5b default |
| PDF | PyMuPDF |
| OCR | Tesseract via pytesseract |
| Email | IMAP with OAuth2 (PKCE), SMTP for password reset |
| Cloud | OneDrive (Microsoft Graph), Google Drive API |
| Security | Fernet (AES-128-CBC), PBKDF2 (480k iterations), session auth, CORS |
| Scheduler | APScheduler |
| Icons | Lucide React |

## Quick Start

### Option A: One-Click Installer (Recommended)

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

**Linux / macOS:**
```bash
bash scripts/install-linux.sh
```

The installer automatically installs Python, Node.js, and Ollama, sets up all dependencies, and creates a launch script.

### Option B: Manual Setup

#### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** (optional, for AI features): [ollama.com](https://ollama.com)
- **Tesseract OCR** (optional, for scanned PDFs): [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract)

```bash
# Backend
cd Regia/backend
python -m venv venv
venv\Scripts\activate  # Windows (or: source venv/bin/activate)
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run build
```

### Run

**Backend** (from `backend/` directory):
```bash
python run.py
```
Ollama starts automatically with the server and pulls the AI model on first run.
The backend serves both the API and the built frontend at **http://localhost:8420**.

**Frontend dev server** (optional, from `frontend/` directory):
```bash
npm run dev
```
Opens at **http://localhost:5173** with hot reload (proxies API to the backend).

**LAN access:**
Open `http://<your-LAN-IP>:8420` from any device on the network.

### Standalone Desktop App (No Browser)

```bash
cd frontend
npm run tauri:dev    # Development
npm run tauri:build  # Build installer (.exe/.dmg/.deb/.AppImage)
```

Requires [Rust](https://rustup.rs/) to be installed for Tauri builds.

### First-Time Setup

1. **Create your account** — Click "Create account" on the login screen (shown only when no users exist)
2. **Provide an email** — Used for password recovery (optional but recommended)
3. Go to **Settings → Security** and set a master password for credential encryption
4. Go to **Settings → Cloud Storage** and click "Connect with Microsoft" or "Connect with Google"
5. Go to **Settings → Email Accounts** and add your first email account (or use OAuth2 connect)
6. Click **Fetch All Emails** on the Dashboard
7. Toggle **Dark Mode** in the sidebar for a warm, dark theme
8. Browse your documents, search, or chat with Reggie!

### Password Recovery

If you forget your password:
1. Click **"Forgot password?"** on the login screen
2. Enter the email address linked to your account
3. A reset link is sent via SMTP using your first configured email provider
4. Click the link to set a new password

> **Note:** If no email provider is configured, the reset token is logged to the server console for manual recovery.

## Configuration

All settings are configurable through the UI under **Settings**. Configuration is stored at:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\Regia\config.json` |
| Linux | `~/.local/share/Regia/config.json` |
| macOS | `~/Library/Application Support/Regia/config.json` |

### Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate an app-specific password
4. In Regia Settings, add a Gmail account with the app password

### Outlook Setup

1. Enable 2-Factor Authentication on your Microsoft account
2. Generate an app password or use OAuth2 with a registered Azure app
3. In Regia Settings, add an Outlook account

### Mobile / LAN Client Setup

To connect a mobile device or another computer on the same network:
1. Open `http://<server-LAN-IP>:8420` in the browser
2. Or set `regia_server_url` in the browser's localStorage to `http://<server-LAN-IP>:8420`
3. The server's LAN IP is available via `GET /api/network/info`

## Folder Structure

Documents are stored following this naming convention:

```
documents/
└── sender_domain/
    └── 2024-01-15/
        └── John_Smith/
            └── Invoice_January_2024/
                └── invoice_001.pdf
```

Each file includes:
- **SHA-256 hash** verified on write
- **OCR text** extracted and indexed
- **LLM classification** (invoice, receipt, contract, etc.)
- **AI summary** of document content

## API Documentation

When the backend is running, visit **http://localhost:8420/docs** for the interactive Swagger API documentation.

Key endpoints:
- `GET /api/auth/status` — Auth state and user info
- `POST /api/auth/login` — Authenticate with username/password
- `POST /api/auth/forgot-password` — Request password reset email
- `POST /api/auth/reset-password` — Reset password with token
- `GET /api/network/info` — Server LAN IP and port
- `GET /api/dashboard` — Dashboard statistics
- `GET /api/health` — Health check with Ollama status

## Security Model

- **User auth** — PBKDF2-SHA256 password hashing (480,000 iterations) with session tokens
- **Credentials encrypted at rest** using Fernet (AES-128-CBC) with PBKDF2-derived keys
- **One-way data flow** — IMAP connections are strictly read-only (`readonly=True`)
- **No write-back** — The system never modifies, deletes, or sends emails (except password reset emails)
- **Master password** required to unlock the credential store
- **No external data transmission** — All AI processing is local via Ollama
- **Path traversal protection** — File browser enforces base directory boundaries
- **CORS** — Configured for localhost, LAN IPs, and Tauri desktop app

## Roadmap

- [ ] Personal cloud mode (Tailscale integration)
- [ ] Mobile-optimized PWA
- [x] Multi-user support (v0.2.1)
- [ ] Additional document types (images, DOCX, XLSX)
- [ ] Email rules and auto-labeling
- [ ] Export and backup tools
- [x] Desktop packaging — Tauri v2 (v0.2.0)
- [x] Dark mode (v0.2.0)
- [x] Cloud storage sync — OneDrive + Google Drive (v0.2.0)
- [x] Password reset via email (v0.2.1)
- [x] Network discovery + LAN access (v0.2.1)

## License

MIT License — see [LICENSE](LICENSE) for details.

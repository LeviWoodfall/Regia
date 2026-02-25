# Regia

**Intelligent Email Ingestion & Document Management System**

Regia automatically ingests emails from any provider (Gmail, Outlook, custom IMAP), extracts PDF attachments and invoice links, classifies them using a lightweight local LLM, and organizes everything into a structured, searchable document archive — all with a warm, modern UI.

The built-in AI assistant **Reggie** can search across your entire document archive and answer questions conversationally.

---

## Features

- **Multi-Provider Email Ingestion** — Gmail, Outlook, any IMAP server with OAuth2 or app password authentication
- **"Connect with Microsoft/Google" OAuth2** — Secure one-click sign-in for email and cloud storage
- **Cloud Storage Sync** — Automatically sync documents to OneDrive or Google Drive
- **One-Way Data Flow** — Emails are pulled read-only; no write-back access to your accounts
- **PDF Processing** — Extract text, OCR scanned documents, compute SHA-256 integrity hashes
- **Invoice Link Detection** — Automatically detects and downloads invoices from email links
- **Lightweight LLM Classification** — Uses Ollama with ultra-light models (Qwen2.5:0.5b, TinyLlama) with rule-based fallback
- **Fully Offline AI** — Reggie is trained on your data only, never connects to the internet
- **Auto-Start AI Engine** — Ollama starts automatically with the server, model pulled on first run
- **Structured Storage** — Documents stored as `{email}/{date}/{sender}/{subject}/filename`
- **Full-Text Search** — SQLite FTS5 across emails, documents, OCR text, and AI summaries
- **Reggie AI Agent** — Conversational search assistant using RAG over your document archive
- **File System Browser** — Clean file browser with document previews
- **User Authentication** — Username/password login defined during initial setup
- **Dark Mode** — Warm, easy-on-the-eyes dark theme with one-click toggle
- **Encrypted Credentials** — Master password with PBKDF2 key derivation and Fernet encryption
- **Configurable Scheduler** — Control polling frequency, post-processing, and retry behavior
- **Detailed Logging** — Full audit trail with hash verification for every document
- **Standalone Desktop App** — Runs as a native desktop app via Tauri (no browser needed)
- **Cross-Platform** — Windows, Linux, macOS (desktop); Android, iOS (via PWA)
- **One-Click Installer** — Auto-installs all prerequisites (Python, Node.js, Ollama)
- **Self-Contained** — SQLite database, fully self-hosted, no external services required

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLite |
| Frontend | React, TypeScript, TailwindCSS v4, Vite |
| Desktop | Tauri (Rust) — standalone app, no browser needed |
| LLM | Ollama (local only), Qwen2.5:0.5b default |
| PDF | PyMuPDF |
| OCR | Tesseract via pytesseract |
| Email | IMAP with OAuth2 (PKCE) |
| Cloud | OneDrive (Microsoft Graph), Google Drive API |
| Security | Fernet (AES-128-CBC), PBKDF2, session auth |
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
```

### Run

**Backend** (from `backend/` directory):
```bash
python run.py
```
Ollama starts automatically with the server and pulls the AI model on first run.

**Frontend** (from `frontend/` directory):
```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

### Standalone Desktop App (No Browser)

```bash
cd frontend
npm run tauri:dev    # Development
npm run tauri:build  # Build installer (.exe/.dmg/.deb/.AppImage)
```

Requires [Rust](https://rustup.rs/) to be installed for Tauri builds.

### First-Time Setup

1. **Create your login** — Set a username and password on the login screen
2. Go to **Settings → Security** and set a master password for credential encryption
3. Go to **Settings → Cloud Storage** and click "Connect with Microsoft" or "Connect with Google"
4. Go to **Settings → Email Accounts** and add your first email account (or use OAuth2 connect)
5. Click **Fetch All Emails** on the Dashboard
6. Toggle **Dark Mode** in the sidebar for a warm, easy-on-the-eyes theme
7. Browse your documents, search, or chat with Reggie!

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

## Security Model

- **Credentials encrypted at rest** using Fernet (AES-128-CBC) with PBKDF2-derived keys (480,000 iterations)
- **One-way data flow** — IMAP connections are strictly read-only (`readonly=True`)
- **No write-back** — The system never modifies, deletes, or sends emails
- **Master password** required to unlock the credential store
- **No external data transmission** — All processing is local

## Roadmap

- [ ] Personal cloud mode (Tailscale integration)
- [ ] Mobile-optimized PWA
- [ ] Multi-user support
- [ ] Additional document types (images, DOCX, XLSX)
- [ ] Email rules and auto-labeling
- [ ] Export and backup tools
- [ ] Desktop packaging (Tauri/Electron)

## License

MIT License — see [LICENSE](LICENSE) for details.

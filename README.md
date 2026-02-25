# Regia

**Intelligent Email Ingestion & Document Management System**

Regia automatically ingests emails from any provider (Gmail, Outlook, custom IMAP), extracts PDF attachments and invoice links, classifies them using a lightweight local LLM, and organizes everything into a structured, searchable document archive — all with a warm, modern UI.

The built-in AI assistant **Reggie** can search across your entire document archive and answer questions conversationally.

---

## Features

- **Multi-Provider Email Ingestion** — Gmail, Outlook, any IMAP server with OAuth2 or app password authentication
- **One-Way Data Flow** — Emails are pulled read-only; no write-back access to your accounts
- **PDF Processing** — Extract text, OCR scanned documents, compute SHA-256 integrity hashes
- **Invoice Link Detection** — Automatically detects and downloads invoices from email links
- **Lightweight LLM Classification** — Uses Ollama with ultra-light models (Qwen2.5:0.5b, TinyLlama) with rule-based fallback
- **Structured Storage** — Documents stored as `{email}/{date}/{sender}/{subject}/filename`
- **Full-Text Search** — SQLite FTS5 across emails, documents, OCR text, and AI summaries
- **Reggie AI Agent** — Conversational search assistant using RAG over your document archive
- **File System Browser** — Clean file browser with document previews
- **Encrypted Credentials** — Master password with PBKDF2 key derivation and Fernet encryption
- **Configurable Scheduler** — Control polling frequency, post-processing, and retry behavior
- **Detailed Logging** — Full audit trail with hash verification for every document
- **Cross-Platform** — Web-based UI works on Windows, Linux, macOS, Android, iOS
- **Self-Contained** — SQLite database, no external services required (except Ollama for AI)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLite |
| Frontend | React, TypeScript, TailwindCSS, Vite |
| LLM | Ollama (local), Qwen2.5:0.5b default |
| PDF | PyMuPDF |
| OCR | Tesseract via pytesseract |
| Email | IMAP with OAuth2 (PKCE) |
| Security | Fernet (AES-128-CBC), PBKDF2 |
| Scheduler | APScheduler |
| Icons | Lucide React |

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** (optional, for AI features): [ollama.com](https://ollama.com)
- **Tesseract OCR** (optional, for scanned PDFs): [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract)

### 1. Clone and Setup Backend

```bash
cd Regia/backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Setup Frontend

```bash
cd Regia/frontend
npm install
```

### 3. (Optional) Pull a Lightweight LLM

```bash
ollama pull qwen2.5:0.5b
```

### 4. Run

**Backend** (from `backend/` directory):
```bash
python run.py
```

**Frontend** (from `frontend/` directory):
```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

### 5. First-Time Setup

1. Go to **Settings → Security** and set a master password
2. Go to **Settings → Email Accounts** and add your first email account
3. Click **Fetch All Emails** on the Dashboard
4. Browse your documents, search, or chat with Reggie!

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

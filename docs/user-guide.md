# User Journey Guide

Welcome to Regia! This guide walks through the tasks finance, operations, and analyst teams complete every day.

## 1. First Sign-In

1. Launch Regia (desktop app) or open `http://localhost:8420` in your browser.
2. If no account exists yet, click **Create account** and follow the wizard.
3. Otherwise, enter the username/password provided by your admin.
4. Bookmark the page and optionally install the PWA shortcut for faster access.

### Forgot Password Flow
- Click **"Forgot password?"** on the login form.
- Enter your account email; Regia emails a reset link (or admins can share the token from logs).

## 2. Dashboard Overview
- **Fetch All Emails** triggers immediate ingestion for configured accounts.
- KPI cards summarize new invoices, contracts, receipts, and exceptions.
- Scheduler status indicates poller activity; use the Settings → Scheduler tab for more detail.

## 3. Email Review Queue
1. Open **Review Queue** from the sidebar.
2. The left table lists pending emails (subject, sender, date, link count).
3. Click a row to load the full detail on the right.
4. Actions:
   - **Approve** — Processes the email, stores attachments, and archives it.
   - **Reject** — Marks as rejected and optionally triggers downstream workflows.
   - **Archive** — Moves the email out of the queue without processing.
5. Links panel: select an invoice link to preview, open in a new tab, or capture to PDF via Playwright.

## 4. Documents & Search
- **Documents** page lists every stored file with filters by type, sender, and tags.
- **Search** page supports natural-language queries (“Find invoices from SupplyCo last quarter”).
- Click results to preview the document, download, or view metadata (hash, OCR text, AI summary).

## 5. Reggie AI Assistant
- Open **Reggie** in the sidebar.
- Ask questions like “What unpaid invoices do we have from March?”
- Reggie cites documents; click references to open them instantly.

## 6. Theme & Accessibility
- Visit **Settings → Appearance**.
- Choose from curated palettes (Sunset, Ocean, etc.); the active theme is labeled.
- Toggle reduced motion in browser settings if you prefer fewer animations.
- Keyboard shortcuts:
  | Shortcut | Action |
  | --- | --- |
  | `Ctrl/Cmd + K` | Global quick search |
  | `Ctrl/Cmd + Shift + F` | Jump to Search page |
  | `?` | Show shortcuts modal (coming soon) |

## 7. Notifications & Alerts
- Toast notifications surface ingestion failures or capture issues.
- Check the **Logs** page for history with filters by severity.
- Enable desktop notifications in browser prompts to get background alerts while multitasking.

## 8. Tips for Power Users
- Use the **Download all attachments** button on an email thread to zip everything at once.
- “Refresh files” reprocesses an email if new attachments arrive or OCR improves.
- Apply **Rules** under Settings to auto-label invoices, receipts, and newsletters; this reduces queue triage.

## 9. Getting Help
- Consult the [Troubleshooting Guide](./troubleshooting.md) for common issues.
- If something looks off, capture a screenshot and include timestamps when reporting to admins.
- Join the `#regia-users` chat channel for best practices and announcements.

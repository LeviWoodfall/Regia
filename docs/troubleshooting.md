# Logging & Troubleshooting

Use this guide to diagnose issues quickly and communicate clear status updates.

## 1. Log Sources

| Component | Location | Notes |
| --- | --- | --- |
| Backend API | `%APPDATA%/Regia/logs/regia-api.log` (Win) / `~/.local/share/Regia/logs/regia-api.log` (Linux/macOS) | Includes scheduler messages |
| Tauri Desktop | `~/Library/Logs/Regia/` or `%LOCALAPPDATA%/Regia/logs` | Desktop-specific events |
| Playwright Capture | `documents/_link_captures/` | One folder per capture |
| Browser Console | `F12` in frontend dev server | Search for `Regia` prefix |

## 2. Common Issues

### Login Loop
- Symptom: login form reappears with no error.
- Check: `GET /api/auth/status` via browser devtools → if `authenticated: false`, token missing.
- Fix: Clear cookies & localStorage, ensure backend clock is correct, verify SQLite `sessions` table not full.

### Scheduler Not Running
- Symptom: Dashboard shows "Poller stopped".
- Steps:
  1. `GET /api/scheduler/status` to confirm `running`.
  2. If `false`, call `POST /api/scheduler/start` and watch logs for errors.
  3. Ensure accounts are enabled under Settings → Email Accounts (look for `enabled: true`).

### Attachments Missing
- Symptom: email processed but no documents folder.
- Checks:
  - `backend/logs` for `hash collision` or `attachment skipped` messages.
  - Verify `documents/<sender>/<date>/` path exists.
  - Run `python backend/scripts/verify_integrity.py --email-id <ID>` (coming soon) or reprocess via UI “Refresh files”.

### Playwright Capture Failures
- Symptom: Capture button shows error toast.
- Checks:
  1. Verify Playwright is installed on server (`python -m playwright install chromium`).
  2. Confirm link accessible (open in browser).
  3. Inspect `regia-api.log` for `HAS_PLAYWRIGHT=False` or network errors.

### Frontend Build Errors
- Run `npm run lint` and `npm run test` to reveal details.
- Delete `.vite` & `node_modules/.cache` if hot reload behaves oddly.

## 3. Incident Response Template

```
Summary: <one-line description>
Impact: <users affected, duration>
Timeline:
- HH:MM Start
- HH:MM Detection
- HH:MM Mitigation
Root Cause: <initial suspicion>
Next Steps: <permanent fix, follow-up>
```

Store retrospectives in `/docs/incidents/`.

## 4. Diagnostics Commands

```powershell
# Windows: tail backend logs
Get-Content "$env:APPDATA\Regia\logs\regia-api.log" -Wait
```

```bash
# Linux/macOS: follow logs
tail -f ~/.local/share/Regia/logs/regia-api.log
```

```bash
# Verify scheduler jobs table
sqlite3 ~/.local/share/Regia/regia.db "SELECT id, name, status FROM scheduler_jobs"
```

## 5. Support Escalation
- First line: #regia-support chat.
- Escalate to on-call engineer listed in [Admin Guide](./admin-guide.md) if unresolved after 15 minutes.
- Provide logs, steps to reproduce, severity, and attempted mitigations.

## 6. Prevention Checklist
- Keep dependencies patched (`python scripts/run_security_checks.py`).
- Monitor disk capacity and rotate old documents/logs.
- Run Playwright smoke test weekly to ensure capture pipeline works end-to-end.

> Keep this guide current—after each incident, document the new detection signs and fixes.

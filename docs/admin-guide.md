# Admin & Operations Guide

This guide describes how to deploy, operate, and maintain Regia across environments. Every procedure below lists the persona, preconditions, commands, and rollback steps so you can run it during business hours or in a postmortem.

## 1. Environment Matrix

| Environment | URL / Interface | Owners | Notes |
| --- | --- | --- | --- |
| Local Dev | `http://localhost:8420` | Engineers | Default `.env` values, SQLite DB stored under user profile |
| Staging | `https://regia-staging.example.com` | DevOps | Mirrors prod configuration, used for release verification |
| Production | `https://regia.example.com` | IT Ops | High-availability setup, daily backups |

## 2. Deployment Workflow

1. Checkout the tagged release (e.g. `git checkout v0.4.0`).
2. Copy `config.example.json` to the target machine under the OS-specific config path.
3. Run backend migrations (SQLite migrations run automatically on start, but verify logs).
4. Start backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8420 --workers 2
   ```
5. Build and serve frontend assets (if not using bundled backend `dist/`):
   ```bash
   cd frontend
   npm install
   npm run build
   ```
6. If packaging desktop app, run `npm run tauri:build` and distribute the installer artifact.

## 3. Upgrades & Rollbacks

| Action | Steps |
| --- | --- |
| Upgrade | 1. Backup `config.json` and `regia.db`.<br>2. Pull latest tag.<br>3. Re-run `pip install -r requirements.txt` & `npm install`.<br>4. Execute the new tests (`pytest`, `npm run test`, `npm run test:playwright`, `python scripts/run_security_checks.py`).<br>5. Restart services. |
| Rollback | 1. Stop services.<br>2. Restore previous `dist/`, `backend/`, and database backup.<br>3. Re-run smoke tests.<br>4. Announce rollback in status page / chat. |

## 4. Scheduler & Pollers

- **Start/Stop**: Use Settings → Scheduler tab or call `POST /api/scheduler/start` and `/stop`.
- **Status**: `GET /api/scheduler/status` returns `running`, job list, last run times.
- **Job Recovery**: If jobs are stuck, run `DELETE FROM scheduler_jobs WHERE status='running'` and restart the backend; APScheduler will recreate jobs.

## 5. Security Operations

### Credential Store
- Master password stored only in memory; reset via Settings → Security.
- Rotate encrypted credentials quarterly; run `scripts/rotate_credentials.py` (coming soon) and notify users to re-authenticate.

### Dev/Test Login
- Seed or update the deterministic login used by tests and smoke checks:
  ```bash
  python scripts/create_dev_user.py --username dev --password DevPassword!123
  ```
- Disable this user in production environments once CI finishes (delete from `users` table or use the UI).

### Log Locations
| Component | Path | Rotation |
| --- | --- | --- |
| Backend API | `%APPDATA%/Regia/logs/regia-api.log` (Windows) or `~/.local/share/Regia/logs/regia-api.log` | 10 files × 5 MB |
| Scheduler | Same as backend log, prefix `[scheduler]` | 10 files × 5 MB |
| Playwright capture | `documents/_link_captures/` | Cleaned by retention job |

## 6. Backups & Disaster Recovery

1. Stop backend service (or ensure WAL checkpoint).
2. Copy `regia.db`, `documents/`, and `config.json` to secure storage.
3. Verify SHA-256 of backup vs active files.
4. To restore: deploy clean node, copy backups into place, run `python backend/scripts/verify_integrity.py`.

### Retention Targets
- Database: nightly snapshot kept for 30 days.
- Documents: incremental file sync every 4 hours, full copy weekly.
- Logs: 14 days kept locally, 90 days in centralized logging.

## 7. Monitoring & Alerts

| Metric | Source | Threshold |
| --- | --- | --- |
| `/api/health` latency | Uptime check | >2s for 5 min triggers warning |
| Scheduler backlog | `scheduler_jobs` table | >3 consecutive failures alerts on-call |
| Disk usage | OS metrics | >80% triggers capacity alert |
| Playwright capture errors | Backend logs | 5 errors/hour triggers notification |

## 8. Incident Checklist

1. Capture logs (`scripts/export_logs.ps1` or `.sh`).
2. Identify failing component (auth, scheduler, capture, storage).
3. Mitigate: scale up, restart service, clear stuck jobs.
4. Communicate via #regia-status channel. Include ETA.
5. File postmortem in `/docs/incidents/<YYYY-MM-DD>-<slug>.md` (folder coming soon).

## 9. Contact Matrix

| Area | Primary | Backup |
| --- | --- | --- |
| Backend API | @backend-oncall | @staff-engineer |
| Frontend | @frontend-oncall | @design-systems |
| Infra/DevOps | @platform-team | @sre-backup |
| Security | @secops | @compliance |

> Keep this guide updated every release. Outdated runbooks are a Sev-2 by policy.

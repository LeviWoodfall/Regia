# Developer Handbook

Welcome to the Regia engineering stack. This document captures architecture context, local workflows, testing expectations, and release requirements.

## 1. Architecture Snapshot

```
IMAP/Graph APIs --> Email Fetcher --> Processing Pipeline --> SQLite (FTS5)
                                              |                    |
                                              v                    v
                                     Object Storage (documents/)   Reggie AI index
```

- **Backend**: FastAPI app (`backend/app`) exposing REST endpoints, scheduler controls, link capture, and Reggie search.
- **Scheduler**: APScheduler jobs stored in SQLite `scheduler_jobs` table and orchestrated via `EmailScheduler`.
- **Pipeline**: `app/processing/pipeline.py` handles hashing, OCR, classification, and storage.
- **Frontend**: React + Vite + Tailwind UI served from `frontend/`, packaged with Tauri for desktop.
- **Desktop**: Tauri bridges (filesystem, process, notification) for offline/desktop distribution.

## 2. Repository Layout

| Path | Description |
| --- | --- |
| `backend/` | Python FastAPI service, scripts, and tests |
| `frontend/` | React SPA with Vitest + Playwright suites |
| `docs/` | Living documentation (admin, dev, user, troubleshooting) |
| `scripts/` | Cross-cutting utilities (`run_security_checks.py`, `create_dev_user.py`, `check_docs.py`) |
| `.github/workflows/` | CI/CD definitions (backend, frontend, docs) |

## 3. Local Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend
cd ../frontend
npm install

# Seed deterministic dev login (used by Playwright & manual smoke tests)
cd ..
python backend/scripts/create_dev_user.py --username dev --password DevPassword!123
```

Launch services:
- Backend API: `python backend/run.py` (serves API + built frontend on port 8420).
- Frontend dev server: `npm run dev` (port 5173) for hot reload.

## 4. Testing & Quality Gates

| Layer | Command | Notes |
| --- | --- | --- |
| Backend unit/integration | `cd backend && pytest` | Fixtures spin up temporary SQLite DB |
| Security scans | `cd backend && python scripts/run_security_checks.py` | Runs Bandit + Safety |
| Frontend unit/UI | `cd frontend && npm run test -- --run` | Vitest + Testing Library |
| Frontend e2e | `cd frontend && npm run test:playwright` | Boots backend + frontend via Playwright `webServer` block |
| Docs lint | `python scripts/check_docs.py` | Ensures mandatory docs exist & contain required anchors |

> CI enforces the full matrix before merging (see Section 6).

## 5. Data & Fixtures

- SQLite DB lives under user profile; tests create ephemeral DBs via `tests/conftest.py` fixtures.
- Documents/attachments stored under `documents/` relative path. Use sample fixtures in `backend/tests/fixtures/` for fast runs.
- Dev login stored in users table; update via `scripts/create_dev_user.py` instead of direct SQL.

## 6. Continuous Integration

Workflow: `.github/workflows/ci.yml`

- **backend** job: installs Python deps, runs pytest, runs `scripts/run_security_checks.py`.
- **frontend** job: installs Node deps, installs backend deps for Playwright servers, executes `npm run test -- --run`, installs Playwright browsers, runs `npm run test:playwright`.
- **docs** job: executes `python scripts/check_docs.py` to guarantee documentation stays in sync.

Jobs run in parallel; merging to `main` requires all green.

## 7. Release Checklist

1. Update CHANGELOG with Added/Fixed/Docs entries.
2. Update relevant docs under `/docs` plus root README.
3. Bump versions in desktop packaging manifests if needed.
4. Tag release `vX.Y.Z`, build artifacts, smoke-test on Windows + macOS.
5. Publish release notes referencing docs sections.

## 8. Documentation Policy

- Every feature PR must include docs updates (`README.md`, `CHANGELOG.md`, and audience-specific guides).
- Run `python scripts/check_docs.py` locally to avoid CI failures.
- Keep examples platform-specific where necessary (PowerShell vs Bash).

## 9. Support & Ownership

| Area | Owners |
| --- | --- |
| Auth & Security | `@secops` |
| Scheduler & Fetchers | `@backend-team` |
| Frontend UX | `@frontend-team` |
| AI / Reggie | `@ml-team` |
| Docs & Developer Experience | `@dx-champions` |

> Questions? Start in `#regia-dev` Slack channel and open a GitHub Discussion if the answer should be documented permanently.

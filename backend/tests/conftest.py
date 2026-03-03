import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppSettings, EmailAccountConfig
from app.database import Database
from app.main import app, app_state


class DummyScheduler:
    """Minimal scheduler stub for API route tests."""

    def __init__(self):
        self.running = False
        self.jobs: list[dict] = []

    def start(self):  # pragma: no cover - trivial state flip
        self.running = True

    def stop(self):  # pragma: no cover
        self.running = False

    def get_job_status(self):
        return self.jobs

    def set_jobs(self, jobs: list[dict]):
        self.jobs = jobs

    @property
    def is_running(self):
        return self.running


@pytest.fixture
def settings(tmp_path):
    cfg = AppSettings()
    cfg.db_path = str(tmp_path / "regia-test.db")
    cfg.storage.base_dir = str(tmp_path / "storage")
    cfg.log_dir = str(tmp_path / "logs")
    cfg.email_accounts = [
        EmailAccountConfig(id="acct-1", email="acct@example.com", name="Test Inbox"),
    ]
    return cfg


@pytest.fixture
def db(settings):
    return Database(settings.db_path)


@pytest.fixture
def scheduler_stub():
    return DummyScheduler()


@pytest.fixture
def client(settings, db, scheduler_stub):
    app_state.clear()
    app_state["settings"] = settings
    app_state["db"] = db
    app_state["scheduler"] = scheduler_stub

    client = TestClient(app)
    yield client
    app_state.clear()


@pytest.fixture
def test_db(db):
    return db


@pytest.fixture
def test_settings(settings):
    return settings


@pytest.fixture
def test_scheduler(scheduler_stub):
    return scheduler_stub

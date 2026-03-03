from fastapi.testclient import TestClient

from tests.test_review_queue_routes import ensure_account, insert_email


def test_archive_email_moves_remote_and_updates_status(client: TestClient, test_db, monkeypatch):
    ensure_account(test_db)
    email_id = insert_email(test_db, status="processed")

    calls = {"archive": 0, "search": 0, "folders": []}

    class DummyConnector:
        def __init__(self, account):
            self.account = account

        async def connect(self):
            return True

        def select_folder(self, folder, readonly=False):
            calls["folders"].append(folder)

        def search_by_header(self, header, value):
            calls["search"] += 1
            return ["42"]

        def archive_message(self, uid):
            calls["archive"] += 1
            assert uid == "42"

        def disconnect(self):
            pass

    monkeypatch.setattr("app.routes.emails.IMAPConnector", DummyConnector)

    response = client.post(f"/api/emails/{email_id}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"

    row = test_db.execute("SELECT status FROM emails WHERE id = ?", (email_id,))[0]
    assert row["status"] == "archived"
    assert calls["archive"] == 1
    assert calls["search"] >= 1


def test_archive_email_not_found_returns_404(client: TestClient):
    response = client.post("/api/emails/999/archive")
    assert response.status_code == 404
    assert response.json()["detail"] == "Email not found"

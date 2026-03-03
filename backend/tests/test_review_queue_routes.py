from fastapi.testclient import TestClient


def ensure_account(db, account_id="acct-1"):
    db.execute_insert(
        """
        INSERT OR REPLACE INTO email_accounts (id, name, email, provider, enabled)
        VALUES (?, ?, ?, ?, 1)
        """,
        (account_id, "Test Account", "acct@example.com", "imap"),
    )


def insert_email(db, **overrides):
    ensure_account(db)
    payload = {
        "account_id": overrides.get("account_id", "acct-1"),
        "message_id": overrides.get("message_id", "msg-1"),
        "subject": overrides.get("subject", "Needs Review"),
        "sender_email": overrides.get("sender_email", "sender@example.com"),
        "sender_name": overrides.get("sender_name", "Sender"),
        "recipient": overrides.get("recipient", "team@example.com"),
        "body_text": overrides.get("body_text", "See https://example.com/invoice.pdf"),
        "body_html": overrides.get("body_html", "<p>Invoice</p>"),
        "status": overrides.get("status", "pending"),
        "has_attachments": overrides.get("has_attachments", 0),
        "has_invoice_links": overrides.get("has_invoice_links", 1),
    }
    return db.execute_insert(
        """
        INSERT INTO emails (
            account_id, message_id, subject, sender_email, sender_name,
            recipient, body_text, body_html, status, has_attachments, has_invoice_links
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["account_id"],
            payload["message_id"],
            payload["subject"],
            payload["sender_email"],
            payload["sender_name"],
            payload["recipient"],
            payload["body_text"],
            payload["body_html"],
            payload["status"],
            payload["has_attachments"],
            payload["has_invoice_links"],
        ),
    )


def test_review_queue_lists_pending_items(client: TestClient, test_db):
    email_id = insert_email(test_db)
    test_db.execute_insert(
        "INSERT INTO review_queue (email_id, status) VALUES (?, 'pending')",
        (email_id,),
    )

    response = client.get("/api/emails/review-queue", params={"page": 1, "page_size": 20})
    data = response.json()

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["items"][0]["id"] == email_id
    assert data["items"][0]["review_status"] == "pending"


def test_review_queue_approve_processes_email(client: TestClient, test_db, monkeypatch):
    email_id = insert_email(test_db)
    test_db.execute_insert(
        "INSERT INTO review_queue (email_id, status) VALUES (?, 'pending')",
        (email_id,),
    )

    calls = []

    class DummyPipeline:
        def __init__(self, db, settings):
            pass

        async def process_email(self, email_id_param, parsed):
            calls.append(email_id_param)

    monkeypatch.setattr("app.routes.emails.ProcessingPipeline", DummyPipeline)

    response = client.post(f"/api/emails/{email_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert calls == [email_id]

    review_row = test_db.execute("SELECT status FROM review_queue WHERE email_id = ?", (email_id,))[0]
    email_row = test_db.execute("SELECT status FROM emails WHERE id = ?", (email_id,))[0]
    assert review_row["status"] == "approved"
    assert email_row["status"] == "processed"


def test_review_queue_reject_marks_email(client: TestClient, test_db):
    email_id = insert_email(test_db)
    test_db.execute_insert(
        "INSERT INTO review_queue (email_id, status) VALUES (?, 'pending')",
        (email_id,),
    )

    response = client.post(f"/api/emails/{email_id}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    review_row = test_db.execute("SELECT status FROM review_queue WHERE email_id = ?", (email_id,))[0]
    email_row = test_db.execute("SELECT status FROM emails WHERE id = ?", (email_id,))[0]
    assert review_row["status"] == "rejected"
    assert email_row["status"] == "rejected"


def test_review_queue_approve_missing_email_returns_404(client: TestClient):
    response = client.post("/api/emails/9999/approve")
    assert response.status_code == 404
    assert response.json()["detail"] == "Email not in review queue"


def test_review_queue_reject_non_pending_returns_400(client: TestClient, test_db):
    email_id = insert_email(test_db)
    test_db.execute_insert(
        "INSERT INTO review_queue (email_id, status) VALUES (?, 'approved')",
        (email_id,),
    )

    response = client.post(f"/api/emails/{email_id}/reject")

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already reviewed"

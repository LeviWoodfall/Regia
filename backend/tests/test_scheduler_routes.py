from fastapi.testclient import TestClient


def test_scheduler_start_sets_running(client: TestClient, test_scheduler):
    response = client.post("/api/scheduler/start")

    assert response.status_code == 200
    assert response.json()["status"] == "started"
    assert test_scheduler.is_running


def test_scheduler_start_rejected_when_disabled(client: TestClient, test_settings):
    test_settings.scheduler.enabled = False
    response = client.post("/api/scheduler/start")

    assert response.status_code == 400
    assert response.json()["detail"] == "Scheduler disabled in settings"


def test_scheduler_stop_turns_off_scheduler(client: TestClient, test_scheduler):
    client.post("/api/scheduler/start")
    assert test_scheduler.is_running

    response = client.post("/api/scheduler/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "stopped"
    assert not test_scheduler.is_running


def test_scheduler_status_reflects_scheduler_state(client: TestClient, test_scheduler):
    test_scheduler.set_jobs([
        {"id": "job-1", "status": "completed"},
        {"id": "job-2", "status": "running"},
    ])
    client.post("/api/scheduler/start")

    response = client.get("/api/scheduler/status")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is True
    assert body["jobs"] == test_scheduler.jobs

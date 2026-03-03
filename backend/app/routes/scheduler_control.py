"""
Scheduler control routes for manual start/stop/status.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


def _get_scheduler():
    from app.main import app_state
    sched = app_state.get("scheduler")
    if not sched:
        raise HTTPException(500, "Scheduler not initialized")
    return sched


def _get_settings():
    from app.main import app_state
    return app_state.get("settings")


@router.post("/start")
async def start_scheduler():
    scheduler = _get_scheduler()
    settings = _get_settings()
    if not settings or not settings.scheduler.enabled:
        raise HTTPException(400, "Scheduler disabled in settings")
    scheduler.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_scheduler():
    scheduler = _get_scheduler()
    scheduler.stop()
    return {"status": "stopped"}


@router.get("/status")
async def scheduler_status():
    scheduler = _get_scheduler()
    jobs = scheduler.get_job_status()
    return {"running": scheduler.is_running, "jobs": jobs}

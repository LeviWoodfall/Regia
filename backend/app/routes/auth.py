"""
Authentication API routes for Regia.
Handles user setup, login, logout, and session validation.
"""

from fastapi import APIRouter, HTTPException, Request, Response

from app.models import UserSetup, LoginRequest, LoginResponse, ChangePasswordRequest

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _get_auth(request: Request):
    from app.main import app_state
    return app_state.get("auth_manager")


def _get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("regia_token", "")


@router.get("/status")
async def auth_status(request: Request):
    """Check if authentication is set up and current session state."""
    auth = _get_auth(request)
    if not auth:
        return {"setup_completed": False, "authenticated": False}

    token = _get_token(request)
    user = auth.validate_session(token) if token else None

    return {
        "setup_completed": auth.is_setup_completed(),
        "authenticated": user is not None,
        "user": user,
    }


@router.post("/setup")
async def setup_user(data: UserSetup, request: Request):
    """Create the initial admin user during first-time setup."""
    auth = _get_auth(request)
    if not auth:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    if auth.is_setup_completed():
        raise HTTPException(status_code=400, detail="Setup already completed")

    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        result = auth.create_user(data.username, data.password, data.display_name)
        # Auto-login after setup
        login_result = auth.login(data.username, data.password)
        return {**result, "token": login_result["token"], "expires_at": login_result["expires_at"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, request: Request, response: Response):
    """Authenticate and get a session token."""
    auth = _get_auth(request)
    if not auth:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    result = auth.login(data.username, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Set cookie as well for convenience
    response.set_cookie(
        key="regia_token",
        value=result["token"],
        httponly=True,
        samesite="lax",
        max_age=28800,  # 8 hours
    )

    return result


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Invalidate the current session."""
    auth = _get_auth(request)
    token = _get_token(request)

    if auth and token:
        auth.logout(token)

    response.delete_cookie("regia_token")
    return {"message": "Logged out"}


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, request: Request):
    """Change the current user's password."""
    auth = _get_auth(request)
    token = _get_token(request)

    if not auth or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth.validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    success = auth.change_password(user["username"], data.old_password, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    return {"message": "Password changed successfully"}

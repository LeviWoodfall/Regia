"""
Authentication API routes for Regia.
Handles user setup, login, logout, session validation, and password reset.
"""

from fastapi import APIRouter, HTTPException, Request, Response

from app.models import (
    UserSetup, LoginRequest, LoginResponse, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.auth import SMTP_PROVIDERS

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _get_auth(request: Request):
    from app.main import app_state
    return app_state.get("auth_manager")


def _get_settings(request: Request):
    from app.main import app_state
    return app_state.get("settings")


def _get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("regia_token", "")


def _build_smtp_config(settings):
    """Build SMTP config from the first configured email account."""
    if not settings or not settings.email_accounts:
        return None
    for acct in settings.email_accounts:
        if acct.enabled and acct.email:
            provider_smtp = SMTP_PROVIDERS.get(acct.provider, SMTP_PROVIDERS["imap"])
            smtp_host = provider_smtp["host"]
            if not smtp_host and acct.imap_server:
                smtp_host = acct.imap_server.replace("imap.", "smtp.")
            if smtp_host:
                return {
                    "host": smtp_host,
                    "port": provider_smtp["port"],
                    "tls": provider_smtp["tls"],
                    "username": acct.email,
                    "password": acct.client_secret or "",
                    "from_email": acct.email,
                }
    return None


@router.get("/status")
async def auth_status(request: Request):
    """Check if authentication is set up and current session state."""
    auth = _get_auth(request)
    if not auth:
        return {"setup_completed": False, "authenticated": False, "user_count": 0}

    token = _get_token(request)
    user = auth.validate_session(token) if token else None

    return {
        "setup_completed": auth.is_setup_completed(),
        "authenticated": user is not None,
        "user": user,
        "user_count": auth.user_count(),
    }


@router.post("/setup")
async def setup_user(data: UserSetup, request: Request):
    """Create a new user account."""
    auth = _get_auth(request)
    if not auth:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        result = auth.create_user(data.username, data.password, data.email, data.display_name)
        # Auto-login after account creation
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


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, request: Request):
    """Request a password reset email."""
    auth = _get_auth(request)
    settings = _get_settings(request)
    if not auth:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    # Always return success to avoid leaking whether email exists
    token = auth.request_password_reset(data.email)
    if token:
        # Build SMTP config from email accounts
        smtp_config = _build_smtp_config(settings)
        app_url = f"http://{request.headers.get('host', 'localhost:8420')}"
        if smtp_config:
            auth.send_reset_email(data.email, token, app_url, smtp_config)
        else:
            # Log the token for manual recovery if no SMTP configured
            import logging
            logging.getLogger("regia.auth").warning(
                f"No SMTP configured. Password reset token for '{data.email}': {token}"
            )

    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, request: Request):
    """Reset password using a valid reset token."""
    auth = _get_auth(request)
    if not auth:
        raise HTTPException(status_code=503, detail="Auth not initialized")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    success = auth.reset_password(data.token, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return {"message": "Password has been reset. You can now log in."}

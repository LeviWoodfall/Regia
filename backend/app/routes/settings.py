"""
Settings and authentication routes for Regia.
Handles master password setup, credential management, and account configuration.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.models import (
    MasterPasswordSetup, MasterPasswordUnlock, OAuthCredentials,
    EmailAccountCreate, EmailAccountResponse,
)
from app.security import credential_manager
from app.config import EmailAccountConfig, AppSettings, save_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_settings():
    """Dependency to get current app settings."""
    from app.main import app_state
    return app_state["settings"]


def get_db():
    """Dependency to get database."""
    from app.main import app_state
    return app_state["db"]


@router.get("/status")
async def get_status():
    """Get the current application status."""
    return {
        "initialized": credential_manager.is_initialized(),
        "unlocked": credential_manager.is_unlocked,
    }


@router.post("/setup")
async def setup_master_password(data: MasterPasswordSetup):
    """Set up the master password for the first time."""
    if credential_manager.is_initialized():
        raise HTTPException(400, "Master password already set. Use /unlock instead.")

    try:
        credential_manager.setup(data.password)
        return {"status": "ok", "message": "Master password configured successfully"}
    except Exception as e:
        raise HTTPException(500, f"Setup failed: {e}")


@router.post("/unlock")
async def unlock(data: MasterPasswordUnlock):
    """Unlock the credential store with the master password."""
    if not credential_manager.is_initialized():
        raise HTTPException(400, "No master password set. Use /setup first.")

    try:
        credential_manager.setup(data.password)
        return {"status": "ok", "message": "Unlocked successfully"}
    except ValueError:
        raise HTTPException(401, "Invalid master password")


@router.post("/lock")
async def lock():
    """Lock the credential store."""
    credential_manager.lock()
    return {"status": "ok", "message": "Locked"}


@router.get("/accounts")
async def list_accounts(settings: AppSettings = Depends(get_settings)):
    """List all configured email accounts with full poller settings."""
    accounts = []
    for acc in settings.email_accounts:
        acct = {
            "id": acc.id,
            "name": acc.name,
            "email": acc.email,
            "provider": acc.provider,
            "enabled": acc.enabled,
            "has_credentials": credential_manager.has_credentials(acc.id) if credential_manager.is_unlocked else False,
            # Poller settings
            "poll_interval_minutes": acc.poll_interval_minutes,
            "folders": acc.folders,
            "search_criteria": acc.search_criteria,
            "only_with_attachments": acc.only_with_attachments,
            "max_emails_per_fetch": acc.max_emails_per_fetch,
            "skip_older_than_days": acc.skip_older_than_days,
            "post_action": acc.post_action,
            "post_action_folder": acc.post_action_folder,
            "download_invoice_links": acc.download_invoice_links,
            "max_attachment_size_mb": acc.max_attachment_size_mb,
        }
        accounts.append(acct)
    return {"accounts": accounts}


@router.post("/accounts")
async def add_account(
    data: EmailAccountCreate,
    settings: AppSettings = Depends(get_settings),
    db=Depends(get_db),
):
    """Add a new email account."""
    account = EmailAccountConfig(
        name=data.name,
        email=data.email,
        provider=data.provider,
        imap_server=data.imap_server,
        imap_port=data.imap_port,
        use_ssl=data.use_ssl,
        auth_method=data.auth_method,
        client_id=data.client_id,
        client_secret=data.client_secret,
        poll_interval_minutes=data.poll_interval_minutes,
        folders=data.folders,
        mark_as_read=data.mark_as_read,
        move_to_folder=data.move_to_folder,
        max_attachment_size_mb=data.max_attachment_size_mb,
        download_invoice_links=data.download_invoice_links,
    )

    # Auto-detect IMAP server for known providers
    if data.provider == "gmail" and not data.imap_server:
        account.imap_server = "imap.gmail.com"
    elif data.provider == "outlook" and not data.imap_server:
        account.imap_server = "outlook.office365.com"

    settings.email_accounts.append(account)
    save_config(settings)

    # Add to database
    db.execute_insert(
        """INSERT INTO email_accounts (id, name, email, provider, enabled)
        VALUES (?, ?, ?, ?, ?)""",
        (account.id, account.name, account.email, account.provider, 1),
    )

    return {"status": "ok", "account_id": account.id}


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: str,
    updates: Dict[str, Any],
    settings: AppSettings = Depends(get_settings),
):
    """Update an existing email account's settings."""
    for acc in settings.email_accounts:
        if acc.id == account_id:
            # Apply allowed updates
            updatable = [
                "name", "enabled", "poll_interval_minutes", "folders",
                "search_criteria", "only_with_attachments", "max_emails_per_fetch",
                "skip_older_than_days", "post_action", "post_action_folder",
                "mark_as_read", "move_to_folder", "download_invoice_links",
                "max_attachment_size_mb",
            ]
            for key in updatable:
                if key in updates:
                    setattr(acc, key, updates[key])
            save_config(settings)
            return {"status": "ok", "account_id": account_id}

    raise HTTPException(404, "Account not found")


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    settings: AppSettings = Depends(get_settings),
    db=Depends(get_db),
):
    """Delete an email account."""
    settings.email_accounts = [a for a in settings.email_accounts if a.id != account_id]
    save_config(settings)

    if credential_manager.is_unlocked:
        credential_manager.delete_credential(account_id)

    db.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))

    return {"status": "ok"}


@router.post("/accounts/{account_id}/credentials")
async def store_credentials(account_id: str, data: OAuthCredentials):
    """Store credentials for an email account."""
    if not credential_manager.is_unlocked:
        raise HTTPException(403, "Credential store is locked")

    if data.app_password:
        credential_manager.store_credential(
            account_id, "app_password", {"password": data.app_password}
        )
    elif data.access_token:
        credential_manager.store_credential(
            account_id, "oauth2_tokens", {
                "access_token": data.access_token,
                "refresh_token": data.refresh_token or "",
                "token_expiry": data.token_expiry or "",
            }
        )
    else:
        raise HTTPException(400, "Must provide either app_password or access_token")

    return {"status": "ok"}


@router.get("/config")
async def get_config(settings: AppSettings = Depends(get_settings)):
    """Get the current application configuration (excluding secrets)."""
    config = settings.model_dump()
    # Strip any sensitive fields
    for acc in config.get("email_accounts", []):
        acc.pop("client_secret", None)
    return config


@router.put("/config")
async def update_config(
    updates: Dict[str, Any],
    settings: AppSettings = Depends(get_settings),
):
    """Update application configuration."""
    current = settings.model_dump()
    current.update(updates)
    try:
        new_settings = AppSettings(**current)
        save_config(new_settings)
        # Update in-memory settings
        from app.main import app_state
        app_state["settings"] = new_settings
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, f"Invalid configuration: {e}")

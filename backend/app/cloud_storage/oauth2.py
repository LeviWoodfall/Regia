"""
OAuth2 flows for cloud storage providers (OneDrive, Google Drive).
Also handles OAuth2 "Connect with" flows for email providers.
Uses PKCE for security.
"""

import base64
import hashlib
import secrets
import urllib.parse
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import httpx

from app.cloud_storage.providers import CLOUD_OAUTH2_PROVIDERS, EMAIL_OAUTH2_PROVIDERS

logger = logging.getLogger("regia.cloud_oauth2")


@dataclass
class PKCEChallenge:
    """PKCE challenge for OAuth2."""
    code_verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    code_challenge: str = ""
    code_challenge_method: str = "S256"

    def __post_init__(self):
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        self.code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# In-memory store for pending OAuth2 flows (state -> flow data)
_pending_flows: Dict[str, Dict[str, Any]] = {}


def start_oauth2_flow(
    flow_type: str,
    provider: str,
    client_id: str,
    client_secret: str = "",
    redirect_uri: str = "http://localhost:8420/api/oauth2/callback",
    extra_scopes: list = None,
) -> Dict[str, str]:
    """
    Start an OAuth2 authorization flow.
    flow_type: 'cloud_storage' or 'email'
    Returns dict with 'url' and 'state'.
    """
    if flow_type == "cloud_storage":
        providers = CLOUD_OAUTH2_PROVIDERS
    elif flow_type == "email":
        providers = EMAIL_OAUTH2_PROVIDERS
    else:
        raise ValueError(f"Unknown flow type: {flow_type}")

    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}")

    config = providers[provider]
    pkce = PKCEChallenge()
    state = secrets.token_urlsafe(32)

    scopes = list(config["scopes"])
    if extra_scopes:
        scopes.extend(extra_scopes)

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": pkce.code_challenge,
        "code_challenge_method": pkce.code_challenge_method,
        "access_type": "offline",
        "prompt": "consent",
    }

    url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"

    # Store for callback
    _pending_flows[state] = {
        "flow_type": flow_type,
        "provider": provider,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "pkce": pkce,
        "token_url": config["token_url"],
    }

    logger.info(f"Started {flow_type} OAuth2 flow for {provider}")
    return {"url": url, "state": state}


async def exchange_oauth2_code(code: str, state: str) -> Dict[str, Any]:
    """Exchange authorization code for tokens after callback."""
    flow = _pending_flows.pop(state, None)
    if not flow:
        raise ValueError("Invalid or expired state parameter")

    data = {
        "client_id": flow["client_id"],
        "code": code,
        "code_verifier": flow["pkce"].code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": flow["redirect_uri"],
    }

    if flow["client_secret"]:
        data["client_secret"] = flow["client_secret"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            flow["token_url"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        tokens = response.json()

    logger.info(f"OAuth2 token exchange successful for {flow['provider']}")
    return {
        "flow_type": flow["flow_type"],
        "provider": flow["provider"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_in": tokens.get("expires_in", 3600),
        "token_type": tokens.get("token_type", "Bearer"),
        "scope": tokens.get("scope", ""),
    }


async def refresh_oauth2_token(
    provider: str,
    refresh_token: str,
    client_id: str,
    client_secret: str = "",
    flow_type: str = "cloud_storage",
) -> Dict[str, Any]:
    """Refresh an expired OAuth2 access token."""
    if flow_type == "cloud_storage":
        providers = CLOUD_OAUTH2_PROVIDERS
    else:
        providers = EMAIL_OAUTH2_PROVIDERS

    config = providers[provider]

    data = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with httpx.AsyncClient() as client:
        response = await client.post(
            config["token_url"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        tokens = response.json()

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", refresh_token),
        "expires_in": tokens.get("expires_in", 3600),
    }

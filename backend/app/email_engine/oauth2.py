"""
OAuth2 authentication flows for Gmail and Outlook.
Implements PKCE flow for secure token acquisition without exposing secrets.
"""

import base64
import hashlib
import secrets
import urllib.parse
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import httpx

from app.config import EmailAccountConfig


# === Provider OAuth2 Endpoints ===

OAUTH2_PROVIDERS = {
    "gmail": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://mail.google.com/"],  # Read-only IMAP access
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
    },
    "outlook": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "https://outlook.office365.com/IMAP.AccessAsUser.All",
            "offline_access",
        ],
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
    },
}


@dataclass
class PKCEChallenge:
    """PKCE (Proof Key for Code Exchange) challenge for OAuth2."""
    code_verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    code_challenge: str = ""
    code_challenge_method: str = "S256"

    def __post_init__(self):
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        self.code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class OAuth2Flow:
    """Manages OAuth2 authentication flows for email providers."""

    def __init__(self, provider: str, client_id: str, client_secret: str = "",
                 redirect_uri: str = "http://localhost:8420/api/oauth2/callback"):
        if provider not in OAUTH2_PROVIDERS:
            raise ValueError(f"Unsupported OAuth2 provider: {provider}")

        self.provider = provider
        self.provider_config = OAUTH2_PROVIDERS[provider]
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._pkce: Optional[PKCEChallenge] = None
        self._state: Optional[str] = None

    def get_authorization_url(self) -> Dict[str, str]:
        """
        Generate the OAuth2 authorization URL with PKCE.
        Returns dict with 'url' and 'state' for CSRF verification.
        """
        self._pkce = PKCEChallenge()
        self._state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.provider_config["scopes"]),
            "state": self._state,
            "code_challenge": self._pkce.code_challenge,
            "code_challenge_method": self._pkce.code_challenge_method,
            "access_type": "offline",  # For refresh tokens
            "prompt": "consent",
        }

        url = f"{self.provider_config['auth_url']}?{urllib.parse.urlencode(params)}"
        return {"url": url, "state": self._state}

    async def exchange_code(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        Validates state parameter to prevent CSRF attacks.
        """
        if state != self._state:
            raise ValueError("Invalid state parameter - possible CSRF attack")

        if not self._pkce:
            raise RuntimeError("No PKCE challenge found - call get_authorization_url first")

        data = {
            "client_id": self.client_id,
            "code": code,
            "code_verifier": self._pkce.code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.provider_config["token_url"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            tokens = response.json()

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_in": tokens.get("expires_in", 3600),
            "token_type": tokens.get("token_type", "Bearer"),
            "scope": tokens.get("scope", ""),
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.provider_config["token_url"],
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


def get_imap_config(provider: str) -> Dict[str, Any]:
    """Get IMAP server configuration for a provider."""
    if provider in OAUTH2_PROVIDERS:
        return {
            "server": OAUTH2_PROVIDERS[provider]["imap_server"],
            "port": OAUTH2_PROVIDERS[provider]["imap_port"],
        }
    return {}

"""
Security module for Regia.
Handles credential encryption, OAuth2 token management, and master password derivation.
All credentials are encrypted at rest using Fernet (AES-128-CBC) with PBKDF2-derived keys.
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import CREDENTIALS_PATH, APP_DATA_DIR


SALT_PATH = APP_DATA_DIR / ".salt"


class CredentialManager:
    """
    Manages encrypted credential storage.
    Credentials are encrypted with a key derived from the user's master password.
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._unlocked = False

    @property
    def is_unlocked(self) -> bool:
        return self._unlocked

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new one."""
        if SALT_PATH.exists():
            return SALT_PATH.read_bytes()
        salt = os.urandom(16)
        SALT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SALT_PATH.write_bytes(salt)
        return salt

    def _derive_key(self, master_password: str) -> bytes:
        """Derive encryption key from master password using PBKDF2."""
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return key

    def setup(self, master_password: str) -> bool:
        """
        Initialize the credential store with a master password.
        Returns True if this is a new setup, False if unlocking existing.
        """
        key = self._derive_key(master_password)
        self._fernet = Fernet(key)

        if CREDENTIALS_PATH.exists():
            # Try to decrypt existing store to verify password
            try:
                self._load_store()
                self._unlocked = True
                return False
            except InvalidToken:
                self._fernet = None
                self._unlocked = False
                raise ValueError("Invalid master password")
        else:
            # New setup - create empty store
            self._save_store({})
            self._unlocked = True
            return True

    def lock(self):
        """Lock the credential store."""
        self._fernet = None
        self._unlocked = False

    def _load_store(self) -> Dict[str, Any]:
        """Load and decrypt the credential store."""
        if not self._fernet:
            raise RuntimeError("Credential store is locked")
        encrypted = CREDENTIALS_PATH.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        return json.loads(decrypted.decode())

    def _save_store(self, store: Dict[str, Any]):
        """Encrypt and save the credential store."""
        if not self._fernet:
            raise RuntimeError("Credential store is locked")
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(store).encode()
        encrypted = self._fernet.encrypt(data)
        CREDENTIALS_PATH.write_bytes(encrypted)

    def store_credential(self, account_id: str, cred_type: str, data: Dict[str, str]):
        """
        Store a credential for an email account.
        cred_type: 'oauth2_tokens', 'app_password'
        """
        store = self._load_store()
        if account_id not in store:
            store[account_id] = {}
        store[account_id][cred_type] = data
        self._save_store(store)

    def get_credential(self, account_id: str, cred_type: str) -> Optional[Dict[str, str]]:
        """Retrieve a credential for an email account."""
        store = self._load_store()
        return store.get(account_id, {}).get(cred_type)

    def delete_credential(self, account_id: str):
        """Delete all credentials for an account."""
        store = self._load_store()
        store.pop(account_id, None)
        self._save_store(store)

    def has_credentials(self, account_id: str) -> bool:
        """Check if credentials exist for an account."""
        store = self._load_store()
        return account_id in store and len(store[account_id]) > 0

    def is_initialized(self) -> bool:
        """Check if the credential store has been set up."""
        return CREDENTIALS_PATH.exists()


# Singleton instance
credential_manager = CredentialManager()


def hash_file(filepath: str, algorithm: str = "sha256") -> str:
    """Compute hash of a file for integrity verification."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def verify_file_hash(filepath: str, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Verify a file's hash matches the expected value."""
    return hash_file(filepath, algorithm) == expected_hash

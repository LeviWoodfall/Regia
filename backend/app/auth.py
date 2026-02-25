"""
User authentication for Regia.
Handles user registration, login, session management, and password hashing.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from app.database import Database

logger = logging.getLogger("regia.auth")

HASH_ITERATIONS = 480_000


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """Hash a password with PBKDF2-SHA256. Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_bytes(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITERATIONS)
    return dk.hex() + ":" + salt.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        dk_hex, salt_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITERATIONS)
        return dk.hex() == dk_hex
    except Exception:
        return False


class AuthManager:
    """Manages user authentication and sessions."""

    def __init__(self, db: Database, session_timeout_minutes: int = 480):
        self.db = db
        self.session_timeout = timedelta(minutes=session_timeout_minutes)

    def is_setup_completed(self) -> bool:
        """Check if initial user setup has been completed."""
        rows = self.db.execute("SELECT COUNT(*) as c FROM users")
        return rows[0]["c"] > 0

    def create_user(self, username: str, password: str, display_name: str = "") -> Dict:
        """Create the initial admin user during setup."""
        if self.is_setup_completed():
            raise ValueError("Setup already completed — user exists")

        password_hash = _hash_password(password)
        self.db.execute_insert(
            "INSERT INTO users (username, password_hash, display_name, is_admin) VALUES (?, ?, ?, 1)",
            (username, password_hash, display_name or username),
        )
        logger.info(f"User '{username}' created")
        return {"username": username, "message": "Account created"}

    def login(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and create a session token."""
        rows = self.db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        if not rows:
            logger.warning(f"Login failed: unknown user '{username}'")
            return None

        user = rows[0]
        if not _verify_password(password, user["password_hash"]):
            logger.warning(f"Login failed: bad password for '{username}'")
            return None

        # Create session
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + self.session_timeout
        self.db.execute_insert(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], expires_at.isoformat()),
        )

        # Update last login
        self.db.execute(
            "UPDATE users SET last_login_at = datetime('now') WHERE id = ?",
            (user["id"],),
        )

        logger.info(f"User '{username}' logged in")
        return {
            "token": token,
            "username": user["username"],
            "display_name": user["display_name"],
            "expires_at": expires_at.isoformat(),
        }

    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate a session token, return user info or None."""
        rows = self.db.execute(
            """SELECT s.*, u.username, u.display_name, u.is_admin
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = ?""",
            (token,),
        )
        if not rows:
            return None

        session = rows[0]
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Expired — clean up
            self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        return {
            "user_id": session["user_id"],
            "username": session["username"],
            "display_name": session["display_name"],
            "is_admin": bool(session["is_admin"]),
        }

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return True

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        self.db.execute(
            "DELETE FROM sessions WHERE expires_at < datetime('now')"
        )

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change a user's password."""
        rows = self.db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        if not rows or not _verify_password(old_password, rows[0]["password_hash"]):
            return False

        new_hash = _hash_password(new_password)
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        # Invalidate all sessions for this user
        self.db.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (rows[0]["id"],),
        )
        logger.info(f"Password changed for '{username}'")
        return True

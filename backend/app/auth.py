"""
User authentication for Regia.
Handles user registration, login, session management, password hashing,
password reset via email, and SMTP email sending.
"""

import secrets
import hashlib
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from app.database import Database

logger = logging.getLogger("regia.auth")

HASH_ITERATIONS = 480_000
RESET_TOKEN_EXPIRY_MINUTES = 30

# SMTP settings by provider
SMTP_PROVIDERS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587, "tls": True},
    "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "tls": True},
    "imap": {"host": "", "port": 587, "tls": True},
}


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash a password with PBKDF2-SHA256. Returns 'hash_hex:salt_hex'."""
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
        self._migrate_users_table()

    def _migrate_users_table(self):
        """Add email column if missing (upgrade from v0.1)."""
        try:
            self.db.execute("SELECT email FROM users LIMIT 1")
        except Exception:
            try:
                self.db.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
                logger.info("Migrated users table: added email column")
            except Exception:
                pass

    def user_count(self) -> int:
        """Return the number of registered users."""
        rows = self.db.execute("SELECT COUNT(*) as c FROM users")
        return rows[0]["c"]

    def is_setup_completed(self) -> bool:
        """Check if at least one user has been created."""
        return self.user_count() > 0

    def create_user(self, username: str, password: str, email: str = "", display_name: str = "") -> Dict:
        """Create a new user account."""
        # Check for duplicate username
        existing = self.db.execute("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            raise ValueError("Username already taken")

        password_hash = _hash_password(password)
        self.db.execute_insert(
            "INSERT INTO users (username, email, password_hash, display_name, is_admin) VALUES (?, ?, ?, ?, 1)",
            (username, email, password_hash, display_name or username),
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
            """SELECT s.*, u.username, u.display_name, u.is_admin, u.email
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = ?""",
            (token,),
        )
        if not rows:
            return None

        session = rows[0]
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        return {
            "user_id": session["user_id"],
            "username": session["username"],
            "display_name": session["display_name"],
            "is_admin": bool(session["is_admin"]),
            "email": session.get("email", ""),
        }

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return True

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        self.db.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change a user's password."""
        rows = self.db.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not rows or not _verify_password(old_password, rows[0]["password_hash"]):
            return False

        new_hash = _hash_password(new_password)
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        # Invalidate all sessions for this user
        self.db.execute("DELETE FROM sessions WHERE user_id = ?", (rows[0]["id"],))
        logger.info(f"Password changed for '{username}'")
        return True

    # === Password Reset ===

    def request_password_reset(self, email: str) -> Optional[str]:
        """Generate a password reset token for the user with this email.
        Returns the token if user found, None otherwise."""
        rows = self.db.execute("SELECT * FROM users WHERE email = ?", (email,))
        if not rows:
            logger.warning(f"Password reset requested for unknown email: {email}")
            return None

        user = rows[0]
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

        # Invalidate any existing reset tokens for this user
        self.db.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))

        self.db.execute_insert(
            "INSERT INTO password_reset_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], expires_at.isoformat()),
        )
        logger.info(f"Password reset token created for user '{user['username']}'")
        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a valid reset token."""
        rows = self.db.execute(
            """SELECT prt.*, u.username FROM password_reset_tokens prt
               JOIN users u ON prt.user_id = u.id
               WHERE prt.token = ? AND prt.used = 0""",
            (token,),
        )
        if not rows:
            return False

        reset = rows[0]
        expires_at = datetime.fromisoformat(reset["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            self.db.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
            return False

        # Set new password
        new_hash = _hash_password(new_password)
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, reset["user_id"]),
        )
        # Mark token as used and invalidate all sessions
        self.db.execute("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,))
        self.db.execute("DELETE FROM sessions WHERE user_id = ?", (reset["user_id"],))
        logger.info(f"Password reset completed for user '{reset['username']}'")
        return True

    # === Email Sending for Password Reset ===

    def send_reset_email(self, email: str, reset_token: str, app_url: str,
                         smtp_config: Optional[Dict] = None) -> bool:
        """Send a password reset email via SMTP."""
        rows = self.db.execute("SELECT * FROM users WHERE email = ?", (email,))
        if not rows:
            return False
        user = rows[0]

        reset_link = f"{app_url}/reset-password?token={reset_token}"

        html = f"""
        <div style="font-family: 'Inter', system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #6d3829; font-size: 24px; margin: 0;">Regia</h1>
                <p style="color: #8b6a59; font-size: 13px;">Password Reset</p>
            </div>
            <div style="background: #faf8f5; border: 1px solid #e6ddd0; border-radius: 12px; padding: 24px;">
                <p style="color: #3a1b13; margin-top: 0;">Hi {user['display_name'] or user['username']},</p>
                <p style="color: #5e4940;">You requested a password reset. Click the button below to set a new password:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{reset_link}" style="display: inline-block; padding: 12px 28px;
                       background: linear-gradient(135deg, #ec7520, #dd5b16); color: white;
                       border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #72574b; font-size: 13px;">
                    This link expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes. If you didn't request this, ignore this email.
                </p>
            </div>
            <p style="color: #b49276; font-size: 11px; text-align: center; margin-top: 16px;">Regia &mdash; All data stays on your device</p>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Regia — Password Reset"
        msg["To"] = email
        msg.attach(MIMEText(f"Reset your password: {reset_link}", "plain"))
        msg.attach(MIMEText(html, "html"))

        if not smtp_config:
            logger.error("No SMTP configuration available for sending reset email")
            return False

        try:
            msg["From"] = smtp_config.get("from_email", smtp_config.get("username", ""))
            host = smtp_config["host"]
            port = smtp_config.get("port", 587)

            with smtplib.SMTP(host, port, timeout=15) as server:
                if smtp_config.get("tls", True):
                    server.starttls()
                server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(msg)

            logger.info(f"Password reset email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send reset email to {email}: {e}")
            return False

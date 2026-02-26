"""
IMAP connection manager for Regia.
Handles secure IMAP connections with OAuth2 and app password authentication.
Enforces one-way data flow (read-only access).
"""

import imaplib
import base64
import logging
from typing import Optional, List
from dataclasses import dataclass

from app.config import EmailAccountConfig
from app.security import credential_manager

logger = logging.getLogger("regia.email.connector")


class IMAPConnector:
    """
    Manages IMAP connections to email servers.
    Enforces read-only access - no write operations are permitted.
    """

    def __init__(self, account: EmailAccountConfig):
        self.account = account
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    async def connect(self) -> bool:
        """
        Establish IMAP connection using configured authentication method.
        Returns True on success, False on failure.
        """
        try:
            if self.account.use_ssl:
                self._connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                )
            else:
                self._connection = imaplib.IMAP4(
                    self.account.imap_server,
                    self.account.imap_port,
                )

            if self.account.auth_method == "oauth2":
                await self._authenticate_oauth2()
            elif self.account.auth_method == "app_password":
                self._authenticate_password()
            else:
                raise ValueError(f"Unsupported auth method: {self.account.auth_method}")

            logger.info(f"Connected to {self.account.email} via {self.account.imap_server}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.account.email}: {e}")
            self.disconnect()
            return False

    async def _authenticate_oauth2(self):
        """Authenticate using OAuth2 XOAUTH2 SASL mechanism."""
        creds = credential_manager.get_credential(self.account.id, "oauth2_tokens")
        if not creds or "access_token" not in creds:
            raise ValueError("No OAuth2 tokens found for account")

        access_token = creds["access_token"]
        auth_string = f"user={self.account.email}\x01auth=Bearer {access_token}\x01\x01"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        typ, data = self._connection.authenticate("XOAUTH2", lambda x: auth_bytes.encode())
        if typ != "OK":
            raise imaplib.IMAP4.error(f"OAuth2 authentication failed: {data}")

    def _authenticate_password(self):
        """Authenticate using app password."""
        creds = credential_manager.get_credential(self.account.id, "app_password")
        if not creds or "password" not in creds:
            raise ValueError("No app password found for account")

        self._connection.login(self.account.email, creds["password"])

    def disconnect(self):
        """Close the IMAP connection."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def select_folder(self, folder: str = "INBOX", readonly: bool = True) -> int:
        """
        Select a mailbox folder.
        readonly=True for safe browsing, False when post-processing actions are needed.
        Returns the number of messages in the folder.
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        typ, data = self._connection.select(folder, readonly=readonly)
        if typ != "OK":
            raise imaplib.IMAP4.error(f"Failed to select folder {folder}: {data}")
        return int(data[0])

    def search(self, criteria: str = "UNSEEN") -> List[bytes]:
        """Search for messages matching criteria."""
        if not self._connection:
            raise RuntimeError("Not connected")

        typ, data = self._connection.search(None, criteria)
        if typ != "OK" or not data or not data[0]:
            return []
        return data[0].split()

    def search_by_header(self, header: str, value: str) -> List[bytes]:
        """Search messages by specific header value (e.g., Message-ID)."""
        if not self._connection:
            raise RuntimeError("Not connected")
        typ, data = self._connection.search(None, "HEADER", header, value)
        if typ != "OK" or not data or not data[0]:
            return []
        return data[0].split()

    def fetch_message(self, msg_id: bytes) -> Optional[bytes]:
        """Fetch a complete email message by ID."""
        if not self._connection:
            raise RuntimeError("Not connected")

        typ, data = self._connection.fetch(msg_id, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            return None
        return data[0][1] if isinstance(data[0], tuple) else None

    def fetch_headers(self, msg_id: bytes) -> Optional[bytes]:
        """Fetch only the headers of a message (lightweight)."""
        if not self._connection:
            raise RuntimeError("Not connected")

        typ, data = self._connection.fetch(msg_id, "(RFC822.HEADER)")
        if typ != "OK" or not data or not data[0]:
            return None
        return data[0][1] if isinstance(data[0], tuple) else None

    def mark_as_read(self, msg_id: bytes):
        """Mark a message as seen (read)."""
        if not self._connection:
            raise RuntimeError("Not connected")
        typ, data = self._connection.store(msg_id, '+FLAGS', '\\Seen')
        if typ != "OK":
            raise imaplib.IMAP4.error(f"Failed to mark message {msg_id} as read: {data}")

    def move_message(self, msg_id: bytes, dest_folder: str):
        """Copy message to destination folder and mark original for deletion."""
        if not self._connection:
            raise RuntimeError("Not connected")
        # IMAP doesn't have a native MOVE; copy + delete
        typ, data = self._connection.copy(msg_id, dest_folder)
        if typ != "OK":
            raise imaplib.IMAP4.error(f"Failed to copy message to {dest_folder}: {data}")
        self._connection.store(msg_id, '+FLAGS', '\\Deleted')
        self._connection.expunge()

    def delete_message(self, msg_id: bytes):
        """Mark a message for deletion and expunge."""
        if not self._connection:
            raise RuntimeError("Not connected")
        self._connection.store(msg_id, '+FLAGS', '\\Deleted')
        self._connection.expunge()

    def archive_message(self, msg_id: bytes):
        """Archive a message (move to [Gmail]/All Mail or Archive folder)."""
        if not self._connection:
            raise RuntimeError("Not connected")
        # Try common archive folder names
        for archive_folder in ['[Gmail]/All Mail', 'Archive', 'INBOX.Archive']:
            try:
                typ, data = self._connection.copy(msg_id, archive_folder)
                if typ == "OK":
                    self._connection.store(msg_id, '+FLAGS', '\\Deleted')
                    self._connection.expunge()
                    return
            except Exception:
                continue
        logger.warning(f"No archive folder found; message {msg_id} left in place")

    def create_folder(self, folder: str) -> bool:
        """Create a folder if it doesn't exist."""
        if not self._connection:
            raise RuntimeError("Not connected")
        try:
            typ, data = self._connection.create(folder)
            return typ == "OK"
        except Exception:
            return False  # Folder likely already exists

    def list_folders(self) -> List[str]:
        """List available mailbox folders."""
        if not self._connection:
            raise RuntimeError("Not connected")

        typ, data = self._connection.list()
        if typ != "OK":
            return []

        folders = []
        for item in data:
            if isinstance(item, bytes):
                # Parse folder name from IMAP LIST response
                parts = item.decode().split(' "/"' if '"/"' in item.decode() else " ")
                if parts:
                    folder = parts[-1].strip().strip('"')
                    folders.append(folder)
        return folders

    @property
    def is_connected(self) -> bool:
        """Check if the connection is active."""
        if not self._connection:
            return False
        try:
            self._connection.noop()
            return True
        except Exception:
            return False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()

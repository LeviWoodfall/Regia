"""
Cloud storage sync engine for Regia.
Handles uploading documents to OneDrive and Google Drive.
"""

import os
import json
import logging
from typing import Dict, Any

import httpx

from app.database import Database
from app.cloud_storage.providers import CLOUD_OAUTH2_PROVIDERS

logger = logging.getLogger("regia.cloud_sync")


class CloudSyncEngine:
    """Syncs documents to cloud storage providers."""

    def __init__(self, db: Database):
        self.db = db

    async def sync_document(
        self,
        connection_id: str,
        document_id: int,
        access_token: str,
        provider: str,
        sync_folder: str = "Regia",
    ) -> Dict[str, Any]:
        """Upload a single document to cloud storage."""
        docs = self.db.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        )
        if not docs:
            return {"status": "error", "message": "Document not found"}

        doc = docs[0]
        file_path = doc["stored_path"]

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found on disk"}

        existing = self.db.execute(
            "SELECT * FROM cloud_sync_log WHERE connection_id = ? AND document_id = ? AND status = 'synced'",
            (connection_id, document_id),
        )
        if existing:
            return {"status": "skipped", "message": "Already synced"}

        try:
            if provider == "onedrive":
                result = await self._upload_to_onedrive(
                    access_token, file_path, doc["stored_filename"], sync_folder
                )
            elif provider == "google_drive":
                result = await self._upload_to_google_drive(
                    access_token, file_path, doc["stored_filename"], sync_folder
                )
            else:
                return {"status": "error", "message": f"Unknown provider: {provider}"}

            cloud_path = f"{sync_folder}/{doc['stored_filename']}"
            self.db.execute(
                """INSERT OR REPLACE INTO cloud_sync_log
                   (connection_id, document_id, cloud_path, status, synced_at, cloud_file_id)
                   VALUES (?, ?, ?, 'synced', datetime('now'), ?)""",
                (connection_id, document_id, cloud_path, result.get("file_id", "")),
            )

            self.db.execute(
                """UPDATE cloud_storage_connections
                   SET last_sync_at = datetime('now'),
                       total_synced = (SELECT COUNT(*) FROM cloud_sync_log
                                       WHERE connection_id = ? AND status = 'synced')
                   WHERE id = ?""",
                (connection_id, connection_id),
            )

            logger.info(f"Synced document {document_id} to {provider}/{sync_folder}")
            return {"status": "synced", "cloud_path": cloud_path}

        except Exception as e:
            self.db.execute(
                """INSERT OR REPLACE INTO cloud_sync_log
                   (connection_id, document_id, cloud_path, status, error_message)
                   VALUES (?, ?, ?, 'error', ?)""",
                (connection_id, document_id, "", str(e)),
            )
            logger.error(f"Cloud sync failed for doc {document_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def sync_all_pending(
        self,
        connection_id: str,
        access_token: str,
        provider: str,
        sync_folder: str = "Regia",
    ) -> Dict[str, Any]:
        """Sync all documents not yet synced to a connection."""
        unsynced = self.db.execute(
            """SELECT d.id FROM documents d
               WHERE d.id NOT IN (
                   SELECT document_id FROM cloud_sync_log
                   WHERE connection_id = ? AND status = 'synced'
               )""",
            (connection_id,),
        )

        results = {"synced": 0, "skipped": 0, "errors": 0}
        for doc in unsynced:
            result = await self.sync_document(
                connection_id, doc["id"], access_token, provider, sync_folder
            )
            if result["status"] == "synced":
                results["synced"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["errors"] += 1

        return results

    async def _upload_to_onedrive(
        self, access_token: str, file_path: str, filename: str, folder: str
    ) -> Dict[str, Any]:
        """Upload a file to OneDrive via Microsoft Graph API."""
        api_base = CLOUD_OAUTH2_PROVIDERS["onedrive"]["api_base"]
        upload_url = f"{api_base}/me/drive/root:/{folder}/{filename}:/content"

        with open(file_path, "rb") as f:
            file_data = f.read()

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                upload_url,
                content=file_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

        return {"file_id": data.get("id", ""), "web_url": data.get("webUrl", "")}

    async def _upload_to_google_drive(
        self, access_token: str, file_path: str, filename: str, folder: str
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive."""
        folder_id = await self._get_or_create_gdrive_folder(access_token, folder)

        metadata = json.dumps({"name": filename, "parents": [folder_id]})

        with open(file_path, "rb") as f:
            file_data = f.read()

        boundary = "regia_upload_boundary"
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{metadata}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--".encode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                content=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

        return {"file_id": data.get("id", "")}

    async def _get_or_create_gdrive_folder(
        self, access_token: str, folder_name: str
    ) -> str:
        """Find or create a folder in Google Drive. Returns folder ID."""
        async with httpx.AsyncClient() as client:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            resp = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                params={"q": query, "fields": "files(id,name)"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            files = resp.json().get("files", [])

            if files:
                return files[0]["id"]

            # Create folder
            resp = await client.post(
                "https://www.googleapis.com/drive/v3/files",
                json={
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()["id"]

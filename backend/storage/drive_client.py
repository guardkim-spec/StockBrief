"""Upload report HTML files to Google Drive."""
import io
import json
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_service():
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    creds_dict = json.loads(settings.google_service_account_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_report_html(date_str: str, html_content: str) -> str:
    """
    Upload HTML report to Drive under StockBrief_v2/reports/YYYY-MM/.
    Returns the file URL or empty string on failure.
    """
    year_month = date_str[:7]  # YYYY-MM
    filename = f"stockbrief_{date_str}.html"

    try:
        service = _get_service()
        folder_id = _ensure_folder(service, year_month)

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "text/html",
        }
        media = MediaIoBaseUpload(
            io.BytesIO(html_content.encode("utf-8")),
            mimetype="text/html",
        )

        # Check if file already exists
        existing = service.files().list(
            q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
            fields="files(id)",
        ).execute().get("files", [])

        if existing:
            file_id = existing[0]["id"]
            service.files().update(
                fileId=file_id,
                media_body=media,
            ).execute()
        else:
            result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()
            file_id = result.get("id", "")

        url = f"https://drive.google.com/file/d/{file_id}/view"
        logger.info("Drive upload success: %s", url)
        return url
    except Exception as exc:
        logger.warning("Drive upload failed (non-fatal): %s", exc)
        return ""


def _ensure_folder(service, year_month: str) -> str:
    """Ensure YYYY-MM subfolder exists under the root folder, return its ID."""
    root_id = settings.google_drive_folder_id
    if not root_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID not set")

    query = (
        f"name='{year_month}' and '{root_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    folder_meta = {
        "name": year_month,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [root_id],
    }
    folder = service.files().create(body=folder_meta, fields="id").execute()
    return folder["id"]
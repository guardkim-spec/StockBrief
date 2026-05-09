"""Send HTML email report via Gmail API."""
import base64
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_service():
    if not settings.gmail_oauth_token:
        raise RuntimeError("GMAIL_OAUTH_TOKEN not set")
    token_data = json.loads(settings.gmail_oauth_token)
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
    )
    return build("gmail", "v1", credentials=creds)


def send_report(date_str: str, html_content: str) -> bool:
    """Send HTML report email. Returns True on success."""
    subject = f"[StockBrief] 일일 주식 브리핑 — {date_str}"
    try:
        service = _get_service()
        msg = MIMEMultipart("alternative")
        msg["to"]      = settings.gmail_recipient
        msg["from"]    = settings.gmail_sender
        msg["subject"] = subject
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Email sent successfully for %s", date_str)
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return False
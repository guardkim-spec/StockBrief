import logging
import json
import os
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")


def _send_gmail_alert(subject: str, body: str) -> None:
    """Send a Gmail alert using the Gmail API OAuth2 credentials."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import base64
        from email.mime.text import MIMEText

        from config.settings import settings

        token_json = settings.gmail_oauth_token
        if not token_json:
            logger.warning("GMAIL_OAUTH_TOKEN not set; skipping alert")
            return

        creds_data = json.loads(token_json)
        creds = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )

        service = build("gmail", "v1", credentials=creds)
        msg = MIMEText(body, "plain", "utf-8")
        msg["to"] = settings.gmail_recipient
        msg["from"] = settings.gmail_sender
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Alert sent: %s", subject)
    except Exception as exc:
        logger.error("Failed to send alert email: %s", exc)


def notify_step_failure(step_name: str, error: Exception) -> None:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    subject = f"[StockBrief] 파이프라인 오류: {step_name} ({now})"
    body = (
        f"StockBrief 파이프라인 단계 [{step_name}] 에서 오류가 발생했습니다.\n\n"
        f"시각: {now}\n"
        f"오류: {type(error).__name__}: {error}\n\n"
        "GitHub Actions 로그를 확인해 주세요."
    )
    _send_gmail_alert(subject, body)


def notify_pipeline_success(date_str: str) -> None:
    subject = f"[StockBrief] 파이프라인 완료: {date_str}"
    body = f"StockBrief 파이프라인이 정상 완료되었습니다.\n날짜: {date_str}"
    _send_gmail_alert(subject, body)


def notify_holiday(date_str: str, market: str) -> None:
    subject = f"[StockBrief] 휴장일 안내: {date_str}"
    body = f"{date_str}은 {market} 휴장일입니다. 데이터 수집을 건너뜁니다."
    _send_gmail_alert(subject, body)

"""Store JSON results to GitHub repository data/ directory."""
import base64
import json
import logging
from datetime import datetime
from typing import Any

import requests
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

_API_BASE = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_file_sha(path: str) -> str | None:
    url = f"{_API_BASE}/repos/{settings.github_owner}/{settings.github_repo}/contents/{path}"
    resp = requests.get(url, headers=_headers(), params={"ref": settings.github_branch})
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def _put_file(path: str, content: str, message: str) -> bool:
    url = f"{_API_BASE}/repos/{settings.github_owner}/{settings.github_repo}/contents/{path}"
    sha = _get_file_sha(path)
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode(),
        "branch": settings.github_branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=payload)
    if resp.status_code == 409:
        # SHA conflict — fetch fresh SHA and retry once
        fresh_sha = _get_file_sha(path)
        if fresh_sha:
            payload["sha"] = fresh_sha
        resp = requests.put(url, headers=_headers(), json=payload)
    if resp.status_code in (200, 201):
        return True
    logger.error("GitHub put failed [%d]: %s — path: %s", resp.status_code, resp.text[:200], path)
    return False


def save_daily_file(date_str: str, filename: str, data: Any) -> bool:
    """Write data/YYYY-MM-DD/<filename> to GitHub."""
    path = f"data/{date_str}/{filename}"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    message = f"data: {date_str}/{filename} [{datetime.now(KST).strftime('%H:%M KST')}]"
    success = _put_file(path, content, message)
    if success:
        logger.info("GitHub: saved %s", path)
    return success


def save_latest(data: Any) -> bool:
    """Overwrite data/latest.json with the full dashboard payload."""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return _put_file("data/latest.json", content, "data: update latest.json")


def save_pipeline_status(date_str: str, steps: list[dict]) -> bool:
    """Overwrite data/pipeline-status.json with current step states."""
    payload = {
        "ok": True,
        "date": date_str,
        "data": {
            "date": date_str,
            "overall": _compute_overall(steps),
            "steps": steps,
        }
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return _put_file("data/pipeline-status.json", content, f"data: pipeline-status [{date_str}]")


def _compute_overall(steps: list[dict]) -> str:
    statuses = [s.get("status", "pending") for s in steps]
    if "failed" in statuses:
        return "failed"
    if "running" in statuses:
        return "running"
    if all(s in ("success", "skipped") for s in statuses):
        return "success"
    return "pending"

import json
import logging
from pathlib import Path
from datetime import date as _date
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


def _latest_data_date() -> str | None:
    """Return the most recent YYYY-MM-DD directory that contains actual pipeline data."""
    data_dir = settings.data_dir
    if not data_dir.exists():
        return None
    dates = sorted(
        [d.name for d in data_dir.iterdir()
         if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"],
        reverse=True,
    )
    return dates[0] if dates else None


def _read_data_file(date_str: str, filename: str) -> dict | None:
    """Try data/YYYY-MM-DD/<filename>, fall back to latest available date, then mock."""
    real = settings.data_dir / date_str / filename
    if real.exists():
        try:
            with open(real, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to read %s: %s", real, exc)

    # Fall back to the latest date that has real pipeline data
    latest = _latest_data_date()
    if latest and latest != date_str:
        fallback = settings.data_dir / latest / filename
        if fallback.exists():
            try:
                with open(fallback, encoding="utf-8") as f:
                    logger.info("Date %s not found; serving %s from %s", date_str, filename, latest)
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to read fallback %s: %s", fallback, exc)

    mock = settings.mock_data_dir / filename
    if mock.exists():
        with open(mock, encoding="utf-8") as f:
            return json.load(f)
    return None


def _read_mock(filename: str) -> dict:
    path = settings.mock_data_dir / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def today_str() -> str:
    import pytz
    from datetime import datetime
    return datetime.now(pytz.timezone("Asia/Seoul")).strftime("%Y-%m-%d")

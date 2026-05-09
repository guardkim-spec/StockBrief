
import json
import logging
from pathlib import Path
from datetime import date as _date
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


def _read_data_file(date_str: str, filename: str) -> dict | None:
    """Try data/YYYY-MM-DD/<filename> first, fall back to shared/mock-data/<filename>."""
    real = settings.data_dir / date_str / filename
    if real.exists():
        try:
            with open(real, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to read %s: %s", real, exc)

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

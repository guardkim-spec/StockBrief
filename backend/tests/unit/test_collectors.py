"""Unit tests for collector utilities."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from collectors.korea_price import _is_korea_holiday, _get_trading_date
from collectors.us_price    import _is_us_holiday, _get_us_trading_date
from datetime import datetime
import pytz

KST = pytz.timezone("Asia/Seoul")


def test_korea_holiday_saturday():
    sat = datetime(2025, 5, 10, 10, 0, tzinfo=KST)  # Saturday
    assert _is_korea_holiday(sat) is True


def test_korea_holiday_sunday():
    sun = datetime(2025, 5, 11, 10, 0, tzinfo=KST)  # Sunday
    assert _is_korea_holiday(sun) is True


def test_korea_weekday_not_holiday():
    mon = datetime(2025, 5, 12, 10, 0, tzinfo=KST)  # Monday (not a holiday)
    # May 12 2025 is not a Korean holiday
    assert _is_korea_holiday(mon) is False


def test_us_holiday_saturday():
    sat = datetime(2025, 5, 10, 10, 0)
    assert _is_us_holiday(sat) is True


def test_trading_date_skips_weekend():
    # May 11 (Sunday) -> should give May 9 (Friday)
    dt = datetime(2025, 5, 11, 10, 0, tzinfo=KST)
    result = _get_trading_date(dt)
    # Result should be a weekday
    from datetime import datetime as dt2
    d = dt2.strptime(result, "%Y%m%d")
    assert d.weekday() < 5
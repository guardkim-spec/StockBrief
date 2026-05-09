"""Unit tests for trend_analyzer."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from analysis.trend_analyzer import _slope_pct, _label_trend, _momentum_score, _compute_ma


def test_slope_uptrend():
    values = [100, 102, 104, 106, 108, 110]
    slope = _slope_pct(values)
    assert slope > 0


def test_slope_downtrend():
    values = [110, 108, 106, 104, 102, 100]
    slope = _slope_pct(values)
    assert slope < 0


def test_slope_flat():
    values = [100.0] * 10
    slope = _slope_pct(values)
    assert abs(slope) < 0.01


def test_label_uptrend():
    assert _label_trend(3.0) == "우상향"


def test_label_downtrend():
    assert _label_trend(-3.0) == "우하향"


def test_label_sideways():
    assert _label_trend(1.0) == "횡보"
    assert _label_trend(-1.0) == "횡보"


def test_momentum_score_range():
    for slope in [-10, -5, -2, 0, 2, 5, 10]:
        score = _momentum_score(slope)
        assert 1 <= score <= 10


def test_compute_ma_length():
    candles = [{"date": f"2025-04-{i+10}", "close": 100 + i} for i in range(10)]
    ma5 = _compute_ma(candles, 5)
    assert len(ma5) == 6  # 10 - 5 + 1


def test_compute_ma_values():
    candles = [{"date": f"2025-04-{i+10}", "close": float(i + 1)} for i in range(5)]
    ma5 = _compute_ma(candles, 5)
    assert len(ma5) == 1
    assert abs(ma5[0]["value"] - 3.0) < 0.01  # (1+2+3+4+5)/5 = 3
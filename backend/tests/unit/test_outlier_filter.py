"""Unit tests for outlier filtering."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD


def test_outlier_threshold_positive():
    change_rate = 35.0
    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
    assert is_outlier is True


def test_outlier_threshold_negative():
    change_rate = -31.0
    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
    assert is_outlier is True


def test_not_outlier():
    change_rate = 5.5
    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
    assert is_outlier is False


def test_boundary_exact():
    change_rate = 30.0
    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
    assert is_outlier is False  # > not >=


def test_threshold_value():
    assert OUTLIER_CHANGE_RATE_THRESHOLD == 30.0
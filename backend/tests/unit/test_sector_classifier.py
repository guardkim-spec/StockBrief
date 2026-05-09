"""Unit tests for sector_classifier."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from analysis.sector_classifier import aggregate_sector_volume, aggregate_sector_news_scores


def test_aggregate_sector_volume_basic():
    stocks = [
        {"sector": "반도체", "volume_amount": 1000},
        {"sector": "반도체", "volume_amount": 2000},
        {"sector": "바이오/헬스케어", "volume_amount": 500},
    ]
    result = aggregate_sector_volume(stocks)
    semicon = next(r for r in result if r["sector"] == "반도체")
    assert semicon["volume_amount"] == 3000
    assert abs(semicon["ratio"] - 3000 / 3500) < 0.001


def test_aggregate_sector_volume_empty():
    assert aggregate_sector_volume([]) == []


def test_aggregate_news_scores_sentiment():
    news = [
        {"sector": "반도체", "sentiment": "positive", "score": 9},
        {"sector": "반도체", "sentiment": "positive", "score": 7},
        {"sector": "바이오/헬스케어", "sentiment": "negative", "score": 3},
    ]
    result = aggregate_sector_news_scores(news)
    semicon = next(r for r in result if r["sector"] == "반도체")
    assert semicon["positive_count"] == 2
    assert semicon["negative_count"] == 0
    assert abs(semicon["avg_score"] - 8.0) < 0.01


def test_aggregate_news_scores_empty():
    assert aggregate_sector_news_scores([]) == []
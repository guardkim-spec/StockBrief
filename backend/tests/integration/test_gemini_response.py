"""Integration tests for Gemini response shape validation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest


def test_news_analysis_prompt_schema():
    """Verify the expected Gemini JSON response shape for news analysis."""
    mock_response = json.dumps([
        {"index": 1, "sector": "반도체", "sentiment": "positive", "score": 8},
        {"index": 2, "sector": "바이오/헬스케어", "sentiment": "negative", "score": 3},
    ])
    parsed = json.loads(mock_response)
    assert isinstance(parsed, list)
    for item in parsed:
        assert "index" in item
        assert "sector" in item
        assert item["sentiment"] in ("positive", "negative", "neutral")
        assert 1 <= item["score"] <= 10


def test_recommendation_prompt_schema():
    """Verify the expected Gemini JSON response shape for sector recommendation."""
    mock_response = json.dumps({
        "sectors": ["반도체", "바이오/헬스케어", "2차전지"],
        "reason": "테스트 추천 근거",
        "confidence": 0.75,
    })
    parsed = json.loads(mock_response)
    assert "sectors" in parsed
    assert len(parsed["sectors"]) == 3
    assert "reason" in parsed
    assert 0.0 <= parsed["confidence"] <= 1.0


def test_sector_names_valid():
    """All sector names in mock recommendation must be in the known sector list."""
    from config.sectors import get_sector_list
    known = set(get_sector_list())
    recommended = ["반도체", "바이오/헬스케어", "2차전지"]
    for sec in recommended:
        assert sec in known, f"{sec!r} is not a valid sector"
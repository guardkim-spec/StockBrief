"""Map raw stock data -> 12 common sectors using shared/sectors.json."""
import logging
from typing import Any

from config.sectors import (
    classify_korea_ticker,
    classify_us_ticker,
    get_sector_list,
)

logger = logging.getLogger(__name__)


def classify_stocks(stocks: list[dict[str, Any]], market: str) -> list[dict[str, Any]]:
    """Fill in sector field for a list of price records."""
    for s in stocks:
        if market == "korea":
            s["sector"] = classify_korea_ticker(s.get("ticker", ""))
        else:
            s["sector"] = classify_us_ticker(
                s.get("ticker", ""),
                s.get("gics_sector", ""),
            )
    return stocks


def aggregate_sector_volume(stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sum trading volume by sector, return sorted list with ratios."""
    totals: dict[str, int] = {}
    for s in stocks:
        sector = s.get("sector", "기타")
        totals[sector] = totals.get(sector, 0) + s.get("volume_amount", 0)

    grand_total = sum(totals.values()) or 1
    result = [
        {
            "sector": sec,
            "volume_amount": vol,
            "ratio": round(vol / grand_total, 4),
        }
        for sec, vol in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]
    return result


def aggregate_sector_news_scores(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate news by sector -> average score and sentiment counts."""
    agg: dict[str, dict] = {}
    for item in news_items:
        sector = item.get("sector") or "기타"
        if sector not in agg:
            agg[sector] = {"positive": 0, "negative": 0, "neutral": 0, "scores": []}
        sentiment = item.get("sentiment", "neutral")
        score = item.get("score", 5)
        agg[sector][sentiment] = agg[sector].get(sentiment, 0) + 1
        agg[sector]["scores"].append(score)

    result = []
    for sector, data in sorted(agg.items(), key=lambda x: sum(x[1]["scores"]) / max(len(x[1]["scores"]), 1), reverse=True):
        scores = data["scores"]
        avg = round(sum(scores) / len(scores), 2) if scores else 0
        result.append({
            "sector": sector,
            "positive_count": data.get("positive", 0),
            "negative_count": data.get("negative", 0),
            "avg_score": avg,
        })
    return result
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
    """Aggregate news by sector -> net sentiment score and counts.

    Only items with a non-empty sector AND non-empty sentiment (i.e. Gemini-analyzed)
    are included so that unanalyzed raw articles don't pollute the scores.
    """
    agg: dict[str, dict] = {}
    for item in news_items:
        sector    = item.get("sector", "").strip()
        sentiment = item.get("sentiment", "").strip()
        # Skip unanalyzed items (empty sector or empty sentiment)
        if not sector or not sentiment:
            continue
        if sector not in agg:
            agg[sector] = {"positive": 0, "negative": 0, "neutral": 0,
                           "pos_scores": [], "neg_scores": []}
        agg[sector][sentiment] = agg[sector].get(sentiment, 0) + 1
        score = item.get("score", 5)
        if sentiment == "positive":
            agg[sector]["pos_scores"].append(score)
        elif sentiment == "negative":
            agg[sector]["neg_scores"].append(score)

    result = []
    for sector, data in agg.items():
        pos_scores = data["pos_scores"]
        neg_scores = data["neg_scores"]
        total      = data["positive"] + data["negative"] + data.get("neutral", 0)
        pos_sum    = sum(pos_scores)
        neg_sum    = sum(neg_scores)
        avg_score  = round((pos_sum + neg_sum) / max(len(pos_scores) + len(neg_scores), 1), 2)

        # Normalised net score in [0, 10]:
        #   5 + (pos_sum - neg_sum) / (total * 10) * 5
        # Dividing by (total * 10) caps the per-article contribution to ±0.5,
        # so you need genuinely many more positives than negatives to reach 10.
        max_possible = total * 10
        net = round(max(0.0, min(10.0,
              5 + (pos_sum - neg_sum) / max_possible * 5)), 2) if max_possible else 5.0

        result.append({
            "sector":         sector,
            "positive_count": data["positive"],
            "negative_count": data["negative"],
            "avg_score":      avg_score,
            "net_score":      net,
        })

    result.sort(key=lambda x: x["net_score"], reverse=True)
    return result
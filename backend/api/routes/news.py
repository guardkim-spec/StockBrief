from fastapi import APIRouter, Query
from ._helpers import _read_data_file, today_str
from analysis.keyword_classifier import apply_keyword_fallback

router = APIRouter()


@router.get("/news")
def get_news(market: str = Query("korea", pattern="^(korea|us)$"), date: str | None = None):
    d = date or today_str()
    filename = f"{market}_news.json"
    raw = _read_data_file(d, filename)
    if raw:
        items = raw.get("data", [])
        lang = "ko" if market == "korea" else "en"

        # Apply keyword-based sector inference for articles not classified by Gemini
        apply_keyword_fallback(items, lang)

        sector_agg: dict = {}
        for item in items:
            s = item.get("sector") or "기타"
            if s not in sector_agg:
                sector_agg[s] = {"positive": 0, "negative": 0, "neutral": 0, "scores": [], "total": 0}
            sent = item.get("sentiment") or "neutral"
            sector_agg[s][sent] = sector_agg[s].get(sent, 0) + 1
            sector_agg[s]["total"] += 1
            score = item.get("score")
            if score:
                sector_agg[s]["scores"].append(score)

        sector_summary = [
            {
                "sector": sector,
                "positive_count": agg["positive"],
                "negative_count": agg["negative"],
                "avg_score": round(sum(agg["scores"]) / len(agg["scores"]), 2) if agg["scores"] else 0,
                "total_count": agg["total"],
            }
            for sector, agg in sorted(
                sector_agg.items(),
                key=lambda x: x[1]["total"],
                reverse=True,
            )
            if sector != "기타"
        ]

        return {
            "ok": True,
            "date": d,
            "data": {
                "market": market,
                "date": d,
                "items": items,
                "sector_summary": sector_summary,
            },
        }
    from ._helpers import _read_mock
    mock = _read_mock("news.json")
    mock["data"]["market"] = market
    return mock


from fastapi import APIRouter, Query
from ._helpers import _read_data_file, today_str

router = APIRouter()

# Keyword-based sector fallback for articles not classified by Gemini
_SECTOR_KEYWORDS_KR: dict[str, list[str]] = {
    "반도체": ["반도체", "삼성전자", "SK하이닉스", "HBM", "파운드리", "DRAM", "낸드", "웨이퍼", "AI반도체", "메모리반도체", "시스템반도체"],
    "2차전지": ["2차전지", "배터리", "LG에너지솔루션", "삼성SDI", "SK온", "양극재", "음극재", "리튬", "전고체"],
    "자동차": ["현대차", "기아차", "기아 ", "완성차", "전기차", "수소차", "자동차"],
    "바이오/헬스케어": ["바이오", "제약", "신약", "FDA", "임상", "헬스케어", "의약품", "셀트리온", "삼성바이오", "한미약품", "파마", "의료기기"],
    "조선/방산": ["조선", "방산", "방위산업", "HD현대중공업", "한화오션", "잠수함", "원전", "방위"],
    "금융": ["은행", "증권", "보험", "한국은행", "금통위", "KB금융", "신한금융", "하나금융", "우리금융"],
    "소비재": ["식품", "유통", "화장품", "롯데쇼핑", "신세계", "이마트", "CJ제일제당", "농심", "오리온", "K뷰티", "뷰티", "해조류", "수산"],
    "철강/소재": ["철강", "포스코", "현대제철", "화학", "소재", "POSCO"],
    "에너지": ["에너지", "정유", "SK이노베이션", "한국전력", "태양광", "LNG", "원유"],
    "IT/소프트웨어": ["카카오", "네이버", "게임", "클라우드", "소프트웨어", "플랫폼", "AI 서비스"],
    "통신/미디어": ["통신", "SKT", "KT", "LG유플러스", "방송", "미디어", "OTT"],
    "부동산/건설": ["건설", "부동산", "아파트", "분양", "GS건설", "현대건설", "대우건설"],
}

_SECTOR_KEYWORDS_US: dict[str, list[str]] = {
    "반도체": ["semiconductor", "NVIDIA", "AMD", "Intel", "TSMC", "chip", "wafer", "HBM", "GPU", "fab"],
    "2차전지": ["battery", "lithium", "EV battery", "Albemarle", "Livent"],
    "자동차": ["automotive", "Tesla", "Ford", "GM", "electric vehicle"],
    "바이오/헬스케어": ["biotech", "pharma", "FDA", "drug approval", "clinical trial", "vaccine", "healthcare"],
    "조선/방산": ["defense", "aerospace", "Lockheed", "Raytheon", "Boeing", "Northrop"],
    "금융": ["bank", "Fed", "interest rate", "JPMorgan", "Goldman Sachs", "financial"],
    "소비재": ["retail", "consumer", "Amazon", "Walmart", "e-commerce", "Target"],
    "철강/소재": ["steel", "materials", "copper", "mining", "Nucor", "Freeport"],
    "에너지": ["oil", "gas", "crude", "ExxonMobil", "Chevron", "energy"],
    "IT/소프트웨어": ["software", "cloud", "AI", "Microsoft", "Google", "Apple", "Meta", "tech"],
    "통신/미디어": ["telecom", "media", "streaming", "Netflix", "Disney", "Comcast"],
    "부동산/건설": ["real estate", "REIT", "construction", "housing"],
}


def _infer_sector(title: str, market: str) -> str:
    kw_map = _SECTOR_KEYWORDS_KR if market == "korea" else _SECTOR_KEYWORDS_US
    for sector, keywords in kw_map.items():
        if any(kw in title for kw in keywords):
            return sector
    return ""


@router.get("/news")
def get_news(market: str = Query("korea", pattern="^(korea|us)$"), date: str | None = None):
    d = date or today_str()
    filename = f"{market}_news.json"
    raw = _read_data_file(d, filename)
    if raw:
        items = raw.get("data", [])

        # Apply keyword-based sector inference as fallback for unclassified articles
        for item in items:
            if not item.get("sector"):
                inferred = _infer_sector(item.get("title", ""), market)
                if inferred:
                    item["sector"] = inferred
                    item["_inferred"] = True

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

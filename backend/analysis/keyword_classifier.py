"""Keyword-based sector classification fallback for when Gemini is unavailable."""
from typing import Any

_SECTOR_KEYWORDS_KR: dict[str, list[str]] = {
    "반도체": ["반도체", "삼성전자", "SK하이닉스", "HBM", "파운드리", "DRAM", "낸드", "웨이퍼", "AI반도체", "메모리반도체", "시스템반도체"],
    "2차전지": ["2차전지", "배터리", "LG에너지솔루션", "삼성SDI", "SK온", "양극재", "음극재", "리튬", "전고체"],
    "자동차": ["현대차", "기아차", "기아 ", "완성차", "전기차", "수소차"],
    "바이오/헬스케어": ["바이오", "제약", "신약", "FDA", "임상", "헬스케어", "의약품", "셀트리온", "삼성바이오", "한미약품", "파마", "의료기기"],
    "조선/방산": ["조선", "방산", "방위산업", "HD현대중공업", "한화오션", "잠수함", "원전", "방위"],
    "금융": ["은행", "증권", "보험", "한국은행", "금통위", "KB금융", "신한금융", "하나금융", "우리금융"],
    "소비재": ["식품", "유통", "화장품", "롯데쇼핑", "신세계", "이마트", "CJ제일제당", "농심", "오리온", "K뷰티", "뷰티", "해조류", "수산"],
    "철강/소재": ["철강", "포스코", "현대제철", "화학", "소재", "POSCO"],
    "에너지": ["에너지", "정유", "SK이노베이션", "한국전력", "태양광", "LNG", "원유"],
    "IT/소프트웨어": ["카카오", "네이버", "게임", "클라우드", "소프트웨어", "플랫폼"],
    "통신/미디어": ["통신", "SKT", "KT", "LG유플러스", "방송", "미디어", "OTT"],
    "부동산/건설": ["건설", "부동산", "아파트", "분양", "GS건설", "현대건설", "대우건설"],
}

_SECTOR_KEYWORDS_EN: dict[str, list[str]] = {
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


def infer_sector(title: str, lang: str) -> str:
    """Return sector name inferred from title keywords, or empty string if no match."""
    kw_map = _SECTOR_KEYWORDS_KR if lang == "ko" else _SECTOR_KEYWORDS_EN
    for sector, keywords in kw_map.items():
        if any(kw in title for kw in keywords):
            return sector
    return ""


def apply_keyword_fallback(items: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """Fill in missing sector for news items using keyword matching."""
    for item in items:
        if not item.get("sector"):
            inferred = infer_sector(item.get("title", ""), lang)
            if inferred:
                item["sector"] = inferred
                item["_inferred"] = True
    return items

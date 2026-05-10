"""Collect Korean stock news from Google News RSS."""
import logging
import random
import time
import hashlib
import time as _time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import feedparser
import pytz

from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

# Each string is passed as the `q` parameter; OR operators and spaces are
# URL-encoded at runtime via _build_url() to avoid malformed query strings.
KOREA_QUERIES = [
    '(소비재 OR 유통 OR 식품 OR 화장품) (실적 OR 수출 OR 성장 OR 흑자전환 OR 어닝서프라이즈)',
    '(한국은행 OR 정부) ("금리 인하" OR "규제 완화" OR 부양책 OR "대규모 투자")',
    '어닝서프라이즈 OR 흑자전환 OR "사상 최대" OR "대규모 수주" OR "독점 공급" OR "M&A"',
    '(반도체 OR 삼성전자 OR SK하이닉스) ("세계 최초" OR 초격차 OR "대규모 수주" OR "독점 공급")',
    '(2차전지 OR 배터리) ("대규모 수주" OR "공장 증설" OR 흑자전환 OR "독점 공급")',
    '(자동차 OR 현대차 OR 기아 OR 전기차) ("사상 최대" OR 어닝서프라이즈 OR "M&A")',
    '(제약 OR 바이오 OR 신약) ("FDA 승인" OR "임상 성공" OR "기술 수출" OR "세계 최초")',
    '(AI OR 로봇 OR 소프트웨어) ("세계 최초" OR 흑자전환 OR "대규모 수주" OR "M&A")',
    '"자사주 소각" OR 무상증자 OR 특별배당 OR 액면분할 OR "주주환원 확대"',
    '(방산 OR 조선 OR 원전) ("수주 잭팟" OR "대규모 수주" OR 흑자전환 OR "사상 최대")',
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _build_url(query: str) -> str:
    """Build a properly URL-encoded Google News RSS URL for the given query."""
    params = urlencode({"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    return f"https://news.google.com/rss/search?{params}"


def _make_id(url: str) -> str:
    return "kr_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _pub_date_str(entry) -> str:
    """Return YYYY-MM-DD from feedparser entry, using published_parsed for RFC 2822 dates."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return _time.strftime("%Y-%m-%d", entry.published_parsed)
    if hasattr(entry, "published") and entry.published:
        raw = entry.published
        if len(raw) >= 10 and raw[4] == "-":
            return raw[:10]
    return ""


def _parse_feed(url: str, cutoff: str) -> list[dict]:
    """Parse a Google News RSS feed. Keeps articles published on or after cutoff date."""
    items = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            pub_date = _pub_date_str(entry)
            # Drop articles older than cutoff; keep if date is unknown
            if pub_date and pub_date < cutoff:
                continue

            items.append({
                "id": _make_id(link),
                "date": pub_date,
                "title": title,
                "url": link,
                "source": "google_news",
                "sector": "",
                "sentiment": "",
                "score": 0,
            })
    except Exception as exc:
        logger.warning("Feed parse error %s: %s", url, exc)
    return items


@retry(max_attempts=3, delay_sec=30.0)
def collect_korea_news(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect Korea stock news from Google News RSS."""
    now_kst = datetime.now(KST)
    today = date_str or now_kst.strftime("%Y-%m-%d")
    logger.info("Collecting Korea news for %s", today)

    # Accept articles within 3 days of the target date (handles past-date runs)
    target_dt = datetime.strptime(today, "%Y-%m-%d")
    cutoff = (target_dt - timedelta(days=2)).strftime("%Y-%m-%d")

    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for query in KOREA_QUERIES:
        url = _build_url(query)
        items = _parse_feed(url, cutoff)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                if not item["date"]:
                    item["date"] = today
                all_items.append(item)
        time.sleep(random.uniform(0.5, 1.5))

    logger.info("Collected %d Korea news articles", len(all_items))
    return all_items

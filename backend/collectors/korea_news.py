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
    "코스피 OR 코스닥 증시 마감 시황",
    "한국은행 OR 금통위 OR 기준금리 OR 환율",
    "어닝서프라이즈 OR 흑자전환 OR 수주 OR 공급계약",
    "삼성전자 OR SK하이닉스 OR 반도체 OR HBM OR 온디바이스",
    "LG에너지솔루션 OR 에코프로 OR 2차전지 OR 전고체",
    "현대차 OR 기아 OR 전기차 OR 자율주행",
    "제약 OR 바이오 OR 임상 OR FDA OR 신약",
    "네이버 OR 카카오 OR 플랫폼 OR 게임 OR AI",
    "금융지주 OR 은행 OR 밸류업 OR 주주환원",
    "방산 OR 조선 OR 원전 OR 수주",
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

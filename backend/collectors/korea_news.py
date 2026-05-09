"""Collect Korean stock news from Naver RSS."""
import logging
import random
import time
import hashlib
from datetime import datetime
from typing import Any

import feedparser
import pytz

from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

NAVER_RSS_URLS = [
    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=259",
]

NAVER_RSS_FEEDS = [
    "https://finance.naver.com/news/news_list.naver?mode=LSPN&category=market_news",
]

STOCK_KEYWORDS = [
    "속보", "단독", "특징주", "급등", "급락", "신고가", "신저가", "상한가", "하한가",
    "실적", "수주", "계약", "투자", "증자", "분기", "호재", "악재", "M&A", "상장",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _make_id(url: str) -> str:
    return "kr_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _parse_feed(url: str, today_str: str) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            pub_date = ""
            if hasattr(entry, "published"):
                pub_date = entry.published[:10] if entry.published else ""

            if pub_date and pub_date != today_str:
                continue

            items.append({
                "id": _make_id(link),
                "date": today_str,
                "title": title,
                "url": link,
                "source": "naver",
                "sector": "",       # filled by Gemini later
                "sentiment": "",    # filled by Gemini later
                "score": 0,         # filled by Gemini later
            })
    except Exception as exc:
        logger.warning("Feed parse error %s: %s", url, exc)
    return items


@retry(max_attempts=3, delay_sec=30.0)
def collect_korea_news(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect today's Korea stock news from Naver RSS. Returns raw items (sector/sentiment TBD)."""
    now_kst = datetime.now(KST)
    today = date_str or now_kst.strftime("%Y-%m-%d")
    logger.info("Collecting Korea news for %s", today)

    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for url in NAVER_RSS_FEEDS:
        items = _parse_feed(url, today)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_items.append(item)
        time.sleep(random.uniform(3.0, 7.0))

    if not all_items:
        logger.info("No Korea news found for %s", today)

    logger.info("Collected %d Korea news articles", len(all_items))
    return all_items
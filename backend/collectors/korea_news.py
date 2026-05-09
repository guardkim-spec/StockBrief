"""Collect Korean stock news from Google News RSS."""
import logging
import random
import time
import hashlib
import time as _time
from datetime import datetime
from typing import Any

import feedparser
import pytz

from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

GOOGLE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=주식+증시+한국&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=코스피+코스닥+반도체&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=한국주식+실적+수주&hl=ko&gl=KR&ceid=KR:ko",
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


def _pub_date_str(entry) -> str:
    """Return YYYY-MM-DD from feedparser entry, using published_parsed for RFC 2822 dates."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return _time.strftime("%Y-%m-%d", entry.published_parsed)
    if hasattr(entry, "published") and entry.published:
        raw = entry.published
        if len(raw) >= 10 and raw[4] == "-":
            return raw[:10]
    return ""


def _parse_feed(url: str, today_str: str) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            pub_date = _pub_date_str(entry)
            if pub_date and pub_date != today_str:
                continue

            items.append({
                "id": _make_id(link),
                "date": today_str,
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

    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for url in GOOGLE_NEWS_RSS:
        items = _parse_feed(url, today)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_items.append(item)
        time.sleep(random.uniform(1.0, 2.0))

    logger.info("Collected %d Korea news articles", len(all_items))
    return all_items

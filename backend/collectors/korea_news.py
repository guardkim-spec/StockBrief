"""Collect Korean stock news from Google News RSS."""
import logging
import random
import time
import hashlib
import time as _time
from datetime import datetime, timedelta
from typing import Any

import feedparser
import pytz

from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

GOOGLE_NEWS_RSS = [
    # General market
    "https://news.google.com/rss/search?q=주식+증시+한국&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=코스피+코스닥+거래&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=한국주식+실적+수주&hl=ko&gl=KR&ceid=KR:ko",
    # Sector-specific
    "https://news.google.com/rss/search?q=반도체+삼성전자+SK하이닉스&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=바이오+제약+헬스케어+임상&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=자동차+현대차+기아+전기차&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=2차전지+배터리+LG에너지솔루션&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=금융+은행+증권+보험&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=IT+인터넷+카카오+네이버&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=조선+방산+철강+소재&hl=ko&gl=KR&ceid=KR:ko",
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

    for url in GOOGLE_NEWS_RSS:
        items = _parse_feed(url, cutoff)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                # Normalize date field to target date if unknown
                if not item["date"]:
                    item["date"] = today
                all_items.append(item)
        time.sleep(random.uniform(0.5, 1.5))

    logger.info("Collected %d Korea news articles", len(all_items))
    return all_items

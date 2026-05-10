"""Collect US stock market news from Google News RSS (no rate limits)."""
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
ET = pytz.timezone("America/New_York")

US_QUERIES = [
    "(Consumer OR Retail OR \"E-commerce\") (\"Earnings Beat\" OR \"Record Sales\" OR \"Revenue Growth\" OR Acquisition)",
    "(\"Federal Reserve\" OR FOMC OR CPI) (\"Rate Cut\" OR Dovish OR \"Soft Landing\")",
    "(Semiconductor OR Nvidia OR \"AI chip\" OR Apple OR Microsoft) (Breakthrough OR Partnership OR \"Record Profits\" OR \"Earnings Beat\")",
    "\"Earnings Beat\" OR \"Raised Guidance\" OR \"Share Buyback\" OR \"Stock Split\" OR Acquisition",
    "(Biotech OR Pharma) (\"FDA Approval\" OR \"Clinical Trial Success\" OR Breakthrough)",
    "(Tesla OR \"electric vehicle\" OR EV) (\"Record Deliveries\" OR Turnaround OR \"Guidance Hike\")",
    "(Amazon OR Google OR Meta OR Netflix) (\"Earnings Beat\" OR \"Share Buyback\" OR \"Record Revenue\" OR \"Stock Split\")",
    "(Energy OR \"crude oil\" OR OPEC) (\"Record Profits\" OR \"Dividend Hike\" OR Acquisition OR Turnaround)",
    "(JPMorgan OR \"Goldman Sachs\" OR Bank) (\"Earnings Beat\" OR \"Dividend Hike\" OR \"Share Buyback\" OR \"Record Profits\")",
    "(Economy OR GDP OR Retail) (\"Soft Landing\" OR Growth OR \"Better than expected\" OR Stimulus)",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _build_url(query: str) -> str:
    params = urlencode({"q": query, "hl": "en", "gl": "US", "ceid": "US:en"})
    return f"https://news.google.com/rss/search?{params}"


def _make_id(url: str) -> str:
    return "us_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _pub_date_str(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return _time.strftime("%Y-%m-%d", entry.published_parsed)
    if hasattr(entry, "published") and entry.published:
        raw = entry.published
        if len(raw) >= 10 and raw[4] == "-":
            return raw[:10]
    return ""


def _parse_feed(url: str, cutoff: str) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue
            pub_date = _pub_date_str(entry)
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
def collect_us_news(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect US market news from Google News RSS."""
    now_et = datetime.now(ET)
    today = date_str or now_et.strftime("%Y-%m-%d")
    logger.info("Collecting US news for %s", today)

    target_dt = datetime.strptime(today, "%Y-%m-%d")
    cutoff = (target_dt - timedelta(days=2)).strftime("%Y-%m-%d")

    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for query in US_QUERIES:
        url = _build_url(query)
        items = _parse_feed(url, cutoff)
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                if not item["date"]:
                    item["date"] = today
                all_items.append(item)
        time.sleep(random.uniform(0.5, 1.5))

    logger.info("Collected %d US news articles", len(all_items))
    return all_items

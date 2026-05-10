"""Collect US stock market news from NewsAPI."""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any

import pytz
import requests

from pipeline.retry import retry
from config.settings import settings

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

NEWSAPI_BASE = "https://newsapi.org/v2/everything"

# Double-quoted phrases are preserved as Python strings with escaped quotes.
# The requests library URL-encodes them automatically (%22) before sending.
# Scheduler: cron "0 10 * * 1-5" → 1 run/day × 6 queries = 6 req/day (limit: 100/day).
US_MARKET_QUERIES = [
    '"S&P 500" OR Nasdaq OR "Dow Jones" OR "Wall Street"',
    '"Federal Reserve" OR FOMC OR "interest rate" OR CPI OR inflation',
    'Semiconductor OR "Artificial Intelligence" OR Nvidia OR Apple OR Microsoft',
    '"earnings report" OR guidance OR "M&A" OR "stock split"',
    'pharma OR biotech OR FDA OR "clinical trial"',
    'Tesla OR EV OR Energy OR oil OR retail',
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _make_id(url: str) -> str:
    return "us_" + hashlib.md5(url.encode()).hexdigest()[:12]


@retry(max_attempts=3, delay_sec=30.0)
def collect_us_news(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect today's US market news from NewsAPI. Returns raw items (sector/sentiment TBD)."""
    if not settings.newsapi_key:
        logger.warning("NEWSAPI_KEY not set; returning empty news list")
        return []

    now_kst = datetime.now(KST)
    today = date_str or now_kst.strftime("%Y-%m-%d")
    logger.info("Collecting US news for %s", today)

    # Expand date range slightly to handle timezone differences and past-date runs
    target_dt = datetime.strptime(today, "%Y-%m-%d")
    from_date = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = today

    all_items: list[dict] = []
    seen_ids: set[str] = set()
    # Hard cap well below 100/day free-tier limit (6 queries × 1 run/day = 6 req/day)
    remaining_requests = 20

    for query in US_MARKET_QUERIES:
        if remaining_requests <= 0:
            break
        try:
            resp = requests.get(
                NEWSAPI_BASE,
                params={
                    "q": query,       # requests encodes quotes → %22 automatically
                    "from": from_date,
                    "to": to_date,
                    "language": "en",
                    "sortBy": "relevancy",
                    "pageSize": 50,
                    "apiKey": settings.newsapi_key,
                },
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            remaining_requests -= 1

            for article in data.get("articles", []):
                url = article.get("url", "").strip()
                title = article.get("title", "").strip()
                if not url or not title or url == "[Removed]" or title == "[Removed]":
                    continue

                item_id = _make_id(url)
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                all_items.append({
                    "id": item_id,
                    "date": today,
                    "title": title,
                    "url": url,
                    "source": "newsapi",
                    "sector": "",
                    "sentiment": "",
                    "score": 0,
                })
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                logger.warning("NewsAPI rate limit reached. Stopping.")
                break
            logger.warning("NewsAPI request failed: %s", exc)
        except Exception as exc:
            logger.warning("NewsAPI error: %s", exc)

    if not all_items:
        logger.info("No US news found for %s", today)

    logger.info("Collected %d US news articles", len(all_items))
    return all_items

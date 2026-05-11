"""Collect US top-100 stocks by dollar volume via Yahoo Finance chart API (curl_cffi)."""
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

import pytz
import holidays as hols

from config.sectors import classify_us_ticker
from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD, TOP_N_STOCKS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")
ET  = pytz.timezone("America/New_York")

_thread_local = threading.local()

LIQUID_US_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","GOOG",
    "JPM","LLY","V","UNH","XOM","MA","JNJ","HD","PG","COST","MRK","ABBV","CRM",
    "ORCL","BAC","CVX","AMD","KO","WMT","PEP","CSCO","ADBE","TMO","ACN","MCD",
    "LIN","ABT","WFC","DIS","PM","ISRG","INTU","IBM","GE","CAT","NOW","BKNG",
    "AXP","TXN","GS","SPGI","RTX","ETN","AMAT","LRCX","KLAC","MU","QCOM","INTC",
    "NFLX","TMUS","CMCSA","T","VZ","NEE","SHW","HON","AMGN","PFE","BMY","GILD",
    "MS","BLK","C","SCHW","USB","PNC","TGT","LOW","TJX","NKE","SBUX","MO",
    "ELV","CI","HUM","CVS","MCK","CNC","F","GM","FCX","NEM","LMT","NOC","BA",
    "GD","LHX","NUE","ALB","RIVN","AMT","PLD","CCI","EQIX","SPG","O","PSA","WELL",
]


def _get_session():
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        from curl_cffi import requests as curl_requests
        _thread_local.session = curl_requests.Session(impersonate="chrome131")
    return _thread_local.session


def _is_us_holiday(dt: datetime) -> bool:
    us_holidays = hols.country_holidays("US", years=dt.year)
    return dt.date() in us_holidays or dt.weekday() >= 5


def _get_us_trading_date(dt: datetime) -> str:
    # Pipeline runs at 10:00 UTC = ~6 AM ET, before market open.
    # Only use today's date if it's past 17:00 ET (after close + buffer).
    d = dt.date()
    if dt.hour < 17:
        d -= timedelta(days=1)
    while True:
        us_holidays = hols.country_holidays("US", years=d.year)
        if d.weekday() < 5 and d not in us_holidays:
            return d.strftime("%Y-%m-%d")
        d -= timedelta(days=1)


def _fetch_ticker(ticker: str, start_ts: int, end_ts: int) -> dict | None:
    time.sleep(random.uniform(0.05, 0.15))
    try:
        session = _get_session()
        resp = session.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"period1": start_ts, "period2": end_ts, "interval": "1d"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.debug("yahoo %s HTTP %d", ticker, resp.status_code)
            return None
        data = resp.json()
        results = data.get("chart", {}).get("result") or []
        if not results:
            return None
        quote = results[0].get("indicators", {}).get("quote", [{}])[0]
        closes  = [c for c in (quote.get("close")  or []) if c is not None]
        volumes = [v for v in (quote.get("volume") or []) if v is not None]
        opens   = [o for o in (quote.get("open")   or []) if o is not None]
        if closes and volumes and closes[0] > 0 and volumes[0] > 0:
            return {
                "close":  closes[0],
                "volume": volumes[0],
                "open":   opens[0] if opens else closes[0],
            }
    except Exception as exc:
        logger.debug("yahoo fetch failed %s: %s", ticker, exc)
    return None


def _build_record(ticker: str, close: float, volume: float, open_p: float, trading_date: str) -> dict:
    volume_amount = int(close * volume)
    change_rate   = round(((close - open_p) / open_p * 100) if open_p > 0 else 0.0, 2)
    return {
        "date":          trading_date,
        "ticker":        ticker,
        "name":          ticker,
        "market":        "NYSE/NASDAQ",
        "sector":        classify_us_ticker(ticker, ""),
        "volume_amount": volume_amount,
        "change_rate":   change_rate,
        "is_outlier":    abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD,
    }


@retry(max_attempts=2, delay_sec=60.0)
def collect_us_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect top-100 US stocks by dollar volume via Yahoo Finance chart API."""
    now_kst = datetime.now(KST)
    if date_str:
        target_kst = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    else:
        target_kst = now_kst

    # Convert KST pipeline date to ET, then roll back to the nearest US trading day.
    # Do NOT do an early holiday check here — the pipeline runs Monday KST but
    # the same midnight converts to Sunday ET, which would incorrectly skip collection.
    target_et = target_kst.astimezone(ET)
    trading_date = _get_us_trading_date(target_et)
    logger.info("Collecting US top-100 for date: %s (via Yahoo Finance)", trading_date)

    start_ts = int(datetime.strptime(trading_date, "%Y-%m-%d")
                   .replace(tzinfo=pytz.UTC).timestamp())
    end_ts   = start_ts + 86400 * 3  # 3-day window

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_fetch_ticker, ticker, start_ts, end_ts): ticker
            for ticker in LIQUID_US_TICKERS
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    results.append(_build_record(
                        ticker, data["close"], data["volume"], data["open"], trading_date
                    ))
            except Exception as exc:
                logger.debug("future error %s: %s", ticker, exc)

    if not results:
        logger.warning("US price: 0 stocks collected — Yahoo Finance may be blocking requests for %s", trading_date)

    results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = results[:TOP_N_STOCKS]
    for idx, item in enumerate(top100, 1):
        item["rank"] = idx

    logger.info("Collected %d US stocks", len(top100))
    return top100

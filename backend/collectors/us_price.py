"""Collect US top-100 stocks by dollar volume using yfinance + curl_cffi."""
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

import pytz
import holidays as hols
import yfinance as yf

from config.sectors import classify_us_ticker
from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD, TOP_N_STOCKS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")
ET = pytz.timezone("America/New_York")

# curl_cffi impersonates Chrome to bypass Yahoo Finance anti-bot blocks.
# One session per thread to avoid thread-safety issues.
_thread_local = threading.local()
_HAS_CURL_CFFI = False
try:
    import curl_cffi  # noqa: F401
    _HAS_CURL_CFFI = True
    logger.debug("curl_cffi available — will impersonate Chrome for Yahoo Finance")
except ImportError:
    logger.warning("curl_cffi not installed; Yahoo Finance requests may be blocked")


def _get_session():
    """Return a thread-local curl_cffi session, or None if unavailable."""
    if not _HAS_CURL_CFFI:
        return None
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        from curl_cffi import requests as curl_requests
        _thread_local.session = curl_requests.Session(impersonate="chrome120")
    return _thread_local.session


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


def _is_us_holiday(dt: datetime) -> bool:
    us_holidays = hols.country_holidays("US", years=dt.year)
    return dt.date() in us_holidays or dt.weekday() >= 5


def _get_us_trading_date(dt: datetime) -> str:
    d = dt.date()
    while True:
        us_holidays = hols.country_holidays("US", years=d.year)
        if d.weekday() < 5 and d not in us_holidays:
            return d.strftime("%Y-%m-%d")
        d -= timedelta(days=1)


def _fetch_ticker(ticker: str, start: str, end: str) -> dict | None:
    """Fetch single ticker OHLCV using curl_cffi-backed session."""
    try:
        session = _get_session()
        kwargs = {"session": session} if session is not None else {}
        t = yf.Ticker(ticker, **kwargs)
        hist = t.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return None
        row = hist.iloc[-1]
        close = float(row.get("Close", 0))
        volume = float(row.get("Volume", 0))
        open_p = float(row.get("Open", close))
        if close <= 0 or volume <= 0:
            return None
        return {"close": close, "volume": volume, "open": open_p}
    except Exception as exc:
        logger.debug("yfinance fetch failed %s: %s", ticker, exc)
        return None


def _build_record(ticker: str, close: float, volume: float, open_p: float, trading_date: str) -> dict:
    volume_amount = int(close * volume)
    change_rate = round(((close - open_p) / open_p * 100) if open_p > 0 else 0.0, 2)
    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
    sector = classify_us_ticker(ticker, "")
    return {
        "date": trading_date,
        "ticker": ticker,
        "name": ticker,
        "market": "NYSE/NASDAQ",
        "sector": sector,
        "volume_amount": volume_amount,
        "change_rate": change_rate,
        "is_outlier": is_outlier,
    }


@retry(max_attempts=3, delay_sec=30.0)
def collect_us_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect top-100 US stocks by dollar volume (individual fetches, parallel)."""
    now_kst = datetime.now(KST)
    if date_str:
        target_kst = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    else:
        target_kst = now_kst

    target_et = target_kst.astimezone(ET)
    if _is_us_holiday(target_et):
        logger.info("US market holiday: %s. Skipping.", target_et.date())
        return []

    trading_date = _get_us_trading_date(target_et)
    next_date = (datetime.strptime(trading_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info("Collecting US top-100 for date: %s", trading_date)

    results: list[dict] = []

    # Parallel individual fetches (max 3 workers to respect rate limits)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_fetch_ticker, ticker, trading_date, next_date): ticker
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
                logger.debug("Futures error for %s: %s", ticker, exc)
            # Light delay between completions to avoid overwhelming Yahoo Finance
            time.sleep(random.uniform(0.05, 0.15))

    results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = results[:TOP_N_STOCKS]
    for idx, item in enumerate(top100, 1):
        item["rank"] = idx

    logger.info("Collected %d US stocks", len(top100))
    return top100

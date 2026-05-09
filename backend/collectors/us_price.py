"""Collect US top-100 stocks by dollar volume.

Primary source: stooq.com (Polish financial data — no auth, reliable)
Fallback source: yfinance + curl_cffi
"""
import csv
import io
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

import requests as http_requests
import pytz
import holidays as hols

from config.sectors import classify_us_ticker
from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD, TOP_N_STOCKS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")
ET  = pytz.timezone("America/New_York")

_STOOQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# yfinance fallback (curl_cffi if available)
_HAS_CURL_CFFI = False
try:
    import curl_cffi  # noqa: F401
    _HAS_CURL_CFFI = True
except ImportError:
    pass

_thread_local = threading.local()


def _get_yf_session():
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


# ── stooq primary ──────────────────────────────────────────────────────────────

def _fetch_stooq(ticker: str, date_str: str) -> dict | None:
    """Fetch OHLCV from stooq.com. Returns None on failure."""
    date_fmt = date_str.replace("-", "")
    url = (
        f"https://stooq.com/q/d/l/"
        f"?s={ticker.lower()}.us&d1={date_fmt}&d2={date_fmt}&i=d"
    )
    try:
        resp = http_requests.get(url, headers=_STOOQ_HEADERS, timeout=15)
        text = resp.text.strip()
        if not text or "No data" in text or text.startswith("<"):
            return None
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            close  = float(row.get("Close",  0) or 0)
            volume = float(row.get("Volume", 0) or 0)
            open_p = float(row.get("Open",   close) or close)
            if close > 0 and volume > 0:
                return {"close": close, "volume": volume, "open": open_p}
    except Exception as exc:
        logger.debug("stooq failed %s: %s", ticker, exc)
    return None


# ── yfinance fallback ──────────────────────────────────────────────────────────

def _fetch_yfinance(ticker: str, start: str, end: str) -> dict | None:
    """Fallback: yfinance with curl_cffi session."""
    try:
        import yfinance as yf
        session = _get_yf_session()
        kwargs  = {"session": session} if session is not None else {}
        t    = yf.Ticker(ticker, **kwargs)
        hist = t.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return None
        row    = hist.iloc[-1]
        close  = float(row.get("Close",  0))
        volume = float(row.get("Volume", 0))
        open_p = float(row.get("Open",   close))
        if close > 0 and volume > 0:
            return {"close": close, "volume": volume, "open": open_p}
    except Exception as exc:
        logger.debug("yfinance fallback failed %s: %s", ticker, exc)
    return None


def _fetch_ticker(ticker: str, trading_date: str, next_date: str) -> dict | None:
    data = _fetch_stooq(ticker, trading_date)
    if data is None:
        data = _fetch_yfinance(ticker, trading_date, next_date)
    return data


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


@retry(max_attempts=3, delay_sec=30.0)
def collect_us_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect top-100 US stocks by dollar volume (stooq primary, yfinance fallback)."""
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
    next_date    = (datetime.strptime(trading_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info("Collecting US top-100 for date: %s (via stooq)", trading_date)

    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=5) as executor:
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
                logger.debug("Future error %s: %s", ticker, exc)

    results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = results[:TOP_N_STOCKS]
    for idx, item in enumerate(top100, 1):
        item["rank"] = idx

    logger.info("Collected %d US stocks via stooq", len(top100))
    return top100

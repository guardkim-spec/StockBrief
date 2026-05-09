"""Collect Korea top-100 stocks by trading value.

Primary: pykrx  →  Fallback: direct KRX HTTP API (bypasses pykrx auth requirement).
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import requests as http_requests
import pytz
import holidays as hols

from config.sectors import classify_korea_ticker
from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD, TOP_N_STOCKS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

_KRX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": (
        "https://data.krx.co.kr/contents/MDC/MDI/indexRequest/"
        "MDCMDI0203.cmd?menuId=MDC0201020101"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

_KRX_MKT_ID = {"KOSPI": "STK", "KOSDAQ": "KSQ"}


def _is_korea_holiday(dt: datetime) -> bool:
    kr_holidays = hols.country_holidays("KR", years=dt.year)
    return dt.date() in kr_holidays or dt.weekday() >= 5


def _get_trading_date(dt: datetime) -> str:
    d = dt.date()
    while True:
        kr_holidays = hols.country_holidays("KR", years=d.year)
        if d.weekday() < 5 and d not in kr_holidays:
            return d.strftime("%Y%m%d")
        d -= timedelta(days=1)


# ── pykrx path ────────────────────────────────────────────────────────────────

def _fetch_via_pykrx(trading_date: str, market_name: str) -> list[dict]:
    try:
        from pykrx import stock
        df = stock.get_market_ohlcv_by_ticker(trading_date, market=market_name)
        if df is None or df.empty:
            return []
        results = []
        for ticker in df.index:
            try:
                row = df.loc[ticker]
                volume_amount = int(row.get("거래대금", 0))
                if volume_amount <= 0:
                    continue
                change_rate = float(row.get("등락률", 0.0))
                name = stock.get_market_ticker_name(ticker)
                sector = classify_korea_ticker(ticker)
                fmt_date = f"{trading_date[:4]}-{trading_date[4:6]}-{trading_date[6:]}"
                results.append({
                    "date": fmt_date,
                    "ticker": ticker,
                    "name": name,
                    "market": market_name,
                    "sector": sector,
                    "volume_amount": volume_amount,
                    "change_rate": round(change_rate, 2),
                    "is_outlier": abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD,
                })
            except Exception as exc:
                logger.debug("Skip ticker %s: %s", ticker, exc)
        return results
    except Exception as exc:
        logger.warning("pykrx failed for %s: %s", market_name, exc)
        return []


# ── Direct KRX API path (fallback) ────────────────────────────────────────────

def _parse_krx_num(val) -> float:
    """Parse KRX number strings like '72,100' or '-1.26'."""
    try:
        return float(str(val).replace(",", "").strip() or 0)
    except (ValueError, TypeError):
        return 0.0


def _fetch_krx_direct(trading_date: str, market_name: str) -> list[dict]:
    """Make direct HTTP calls to KRX data portal without pykrx session."""
    mkt_id = _KRX_MKT_ID.get(market_name, "STK")
    session = http_requests.Session()
    session.headers.update(_KRX_HEADERS)

    # Warm up cookies
    try:
        session.get("https://data.krx.co.kr/", timeout=10)
    except Exception:
        pass

    # Step 1: generate OTP
    otp_resp = session.post(
        "https://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd",
        data={
            "locale": "ko_KR",
            "mktId": mkt_id,
            "trdDd": trading_date,
            "share": "1",
            "money": "1",
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": "dbms/MDC/STAT/standard/MDCSTAT01501",
        },
        timeout=30,
    )
    otp = otp_resp.text.strip()
    if not otp:
        logger.warning("KRX OTP empty for %s %s", market_name, trading_date)
        return []

    # Step 2: fetch data
    data_resp = session.post(
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data={"code": otp},
        timeout=30,
    )
    if not data_resp.text.strip():
        logger.warning("KRX data empty for %s %s", market_name, trading_date)
        return []

    try:
        raw = data_resp.json()
    except Exception as exc:
        logger.warning("KRX JSON parse error for %s: %s", market_name, exc)
        return []

    output = raw.get("OutBlock_1", raw.get("output", []))
    if not output:
        logger.warning("KRX output empty for %s %s", market_name, trading_date)
        return []

    fmt_date = f"{trading_date[:4]}-{trading_date[4:6]}-{trading_date[6:]}"
    results = []
    for item in output:
        try:
            ticker = item.get("ISU_SRT_CD", "").strip()
            if not ticker:
                continue
            name = item.get("ISU_ABBRV", ticker).strip()
            volume_amount = int(_parse_krx_num(item.get("ACC_TRDVAL", 0)))
            if volume_amount <= 0:
                continue
            change_rate = _parse_krx_num(item.get("FLUC_RT", 0))
            sector = classify_korea_ticker(ticker)
            results.append({
                "date": fmt_date,
                "ticker": ticker,
                "name": name,
                "market": market_name,
                "sector": sector,
                "volume_amount": volume_amount,
                "change_rate": round(change_rate, 2),
                "is_outlier": abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD,
            })
        except Exception as exc:
            logger.debug("Skip KRX item: %s", exc)

    logger.info("KRX direct: %d %s stocks", len(results), market_name)
    return results


# ── Public API ────────────────────────────────────────────────────────────────

@retry(max_attempts=3, delay_sec=30.0)
def collect_korea_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect top-100 Korean stocks by trading value."""
    now_kst = datetime.now(KST)
    if date_str:
        target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    else:
        target = now_kst

    if _is_korea_holiday(target):
        logger.info("Korea market holiday: %s. Skipping.", target.date())
        return []

    trading_date = _get_trading_date(target)
    logger.info("Collecting Korea top-100 for date: %s", trading_date)

    all_results: list[dict] = []
    for market_name in ("KOSPI", "KOSDAQ"):
        # Primary: pykrx
        market_data = _fetch_via_pykrx(trading_date, market_name)
        if not market_data:
            # Fallback: direct KRX API
            logger.info("pykrx returned empty for %s, trying direct KRX API", market_name)
            market_data = _fetch_krx_direct(trading_date, market_name)
        all_results.extend(market_data)

    all_results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = all_results[:TOP_N_STOCKS]
    for i, item in enumerate(top100, 1):
        item["rank"] = i

    logger.info("Collected %d Korea stocks", len(top100))
    return top100

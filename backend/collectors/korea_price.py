"""Collect Korea top-100 stocks by trading value using pykrx."""
import logging
from datetime import datetime, timedelta
from typing import Any

import pytz
import holidays as hols
from pykrx import stock

from config.sectors import classify_korea_ticker
from config.schedule import OUTLIER_CHANGE_RATE_THRESHOLD, TOP_N_STOCKS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")


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


@retry(max_attempts=3, delay_sec=30.0)
def collect_korea_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """
    Collect top-100 Korean stocks by trading value.
    Returns list of price schema dicts.
    """
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

    results: list[dict] = []
    for market_name in ("KOSPI", "KOSDAQ"):
        try:
            df = stock.get_market_trading_value_by_ticker(
                trading_date, trading_date, market_name
            )
            if df.empty:
                continue

            ohlcv = stock.get_market_ohlcv_by_ticker(trading_date, market=market_name)

            for ticker in df.index:
                try:
                    volume_amount = int(df.loc[ticker, "거래대금"])
                    if volume_amount <= 0:
                        continue

                    change_rate = 0.0
                    if ticker in ohlcv.index and "등락률" in ohlcv.columns:
                        change_rate = float(ohlcv.loc[ticker, "등락률"])

                    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD
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
                        "is_outlier": is_outlier,
                    })
                except Exception as exc:
                    logger.debug("Skip ticker %s: %s", ticker, exc)
        except Exception as exc:
            logger.warning("Failed to fetch %s data: %s", market_name, exc)

    results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = results[:TOP_N_STOCKS]
    for i, item in enumerate(top100, 1):
        item["rank"] = i

    logger.info("Collected %d Korea stocks", len(top100))
    return top100
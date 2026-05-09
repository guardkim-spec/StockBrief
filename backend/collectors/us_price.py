"""Collect US top-100 stocks by dollar volume using yfinance."""
import logging
import random
import time
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


@retry(max_attempts=3, delay_sec=30.0)
def collect_us_top100(date_str: str | None = None) -> list[dict[str, Any]]:
    """Collect top-100 US stocks by dollar volume."""
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
    batch_size = 20

    for i in range(0, len(LIQUID_US_TICKERS), batch_size):
        batch = LIQUID_US_TICKERS[i : i + batch_size]
        try:
            raw = yf.download(
                tickers=" ".join(batch),
                start=trading_date,
                end=next_date,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
            )
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        df_t = raw
                    else:
                        if ticker not in raw.columns.get_level_values(0):
                            continue
                        df_t = raw[ticker]

                    df_t = df_t.dropna(how="all")
                    if df_t.empty:
                        continue

                    row = df_t.iloc[-1]
                    close = float(row.get("Close", 0))
                    volume = float(row.get("Volume", 0))
                    open_p = float(row.get("Open", close))

                    if close <= 0 or volume <= 0:
                        continue

                    volume_amount = int(close * volume)
                    change_rate = round(((close - open_p) / open_p * 100) if open_p > 0 else 0.0, 2)
                    is_outlier = abs(change_rate) > OUTLIER_CHANGE_RATE_THRESHOLD

                    try:
                        ticker_obj = yf.Ticker(ticker)
                        gics_sector = ticker_obj.info.get("sector", "")
                    except Exception:
                        gics_sector = ""

                    sector = classify_us_ticker(ticker, gics_sector)

                    results.append({
                        "date": trading_date,
                        "ticker": ticker,
                        "name": ticker,
                        "market": "NYSE/NASDAQ",
                        "sector": sector,
                        "volume_amount": volume_amount,
                        "change_rate": change_rate,
                        "is_outlier": is_outlier,
                    })
                except Exception as exc:
                    logger.debug("Skip US ticker %s: %s", ticker, exc)
        except Exception as exc:
            logger.warning("Batch download failed: %s", exc)

        time.sleep(random.uniform(1.5, 4.0))

    results.sort(key=lambda x: x["volume_amount"], reverse=True)
    top100 = results[:TOP_N_STOCKS]
    for idx, item in enumerate(top100, 1):
        item["rank"] = idx

    logger.info("Collected %d US stocks", len(top100))
    return top100
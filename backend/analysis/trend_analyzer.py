"""Analyze 20-day candlestick trend for top sectors."""
import logging
from datetime import datetime, timedelta
from typing import Any

import pytz
import yfinance as yf
import holidays as hols
from pykrx import stock as krx_stock

from config.schedule import TREND_UP_SLOPE_PCT, TREND_DOWN_SLOPE_PCT, CANDLE_DAYS
from pipeline.retry import retry

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")


def _slope_pct(values: list[float]) -> float:
    """Linear regression slope as % change over the series."""
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0 or y_mean == 0:
        return 0.0
    slope = num / den
    return round((slope / y_mean) * 100, 4)


def _label_trend(slope: float) -> str:
    if slope >= TREND_UP_SLOPE_PCT:
        return "우상향"
    if slope <= TREND_DOWN_SLOPE_PCT:
        return "우하향"
    return "횡보"


def _momentum_score(slope: float, volume_ratio: float = 1.0) -> int:
    """1-10 score based on slope magnitude and volume confirmation."""
    base = min(abs(slope) / 2, 5)  # slope contribution capped at 5
    vol_bonus = min((volume_ratio - 1) * 2, 3) if volume_ratio > 1 else 0
    direction = 1 if slope > 0 else -1
    raw = 5 + direction * (base + vol_bonus)
    return max(1, min(10, round(raw)))


def _fetch_korea_candles(ticker: str, days: int = CANDLE_DAYS) -> list[dict]:
    try:
        now = datetime.now(KST)
        end = now.strftime("%Y%m%d")
        start = (now - timedelta(days=days * 2)).strftime("%Y%m%d")  # buffer for holidays
        df = krx_stock.get_market_ohlcv_by_date(start, end, ticker)
        if df.empty:
            return []
        df = df.tail(days)
        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": int(row.get("시가", 0)),
                "high": int(row.get("고가", 0)),
                "low":  int(row.get("저가", 0)),
                "close": int(row.get("종가", 0)),
                "volume": int(row.get("거래량", 0)),
            }
            for idx, row in df.iterrows()
        ]
    except Exception as exc:
        logger.warning("Korea candle fetch failed for %s: %s", ticker, exc)
        return []


def _fetch_us_candles(ticker: str, days: int = CANDLE_DAYS) -> list[dict]:
    try:
        now = datetime.now(KST)
        end = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            return []
        df = df.tail(days)
        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row.get("Open", 0)), 2),
                "high": round(float(row.get("High", 0)), 2),
                "low":  round(float(row.get("Low", 0)), 2),
                "close": round(float(row.get("Close", 0)), 2),
                "volume": int(row.get("Volume", 0)),
            }
            for idx, row in df.iterrows()
        ]
    except Exception as exc:
        logger.warning("US candle fetch failed for %s: %s", ticker, exc)
        return []


def _compute_ma(candles: list[dict], window: int) -> list[dict]:
    closes = [c["close"] for c in candles]
    result = []
    for i in range(window - 1, len(closes)):
        avg = sum(closes[i - window + 1 : i + 1]) / window
        result.append({"date": candles[i]["date"], "value": round(avg, 2)})
    return result


@retry(max_attempts=3, delay_sec=30.0)
def analyze_sector_trend(sector: str, ticker: str, name: str, market: str) -> dict[str, Any]:
    """Fetch 20-day candles and compute trend label + momentum score."""
    if market == "korea":
        candles = _fetch_korea_candles(ticker)
    else:
        candles = _fetch_us_candles(ticker)

    if not candles:
        return {
            "sector": sector, "ticker": ticker, "name": name,
            "trend": "횡보", "momentum_score": 5,
            "candles": [], "ma5": [], "ma20": [],
        }

    closes = [c["close"] for c in candles]
    ma20_values = _compute_ma(candles, 20)
    slope = _slope_pct([m["value"] for m in ma20_values]) if ma20_values else _slope_pct(closes)

    avg_early_vol = sum(c["volume"] for c in candles[:5]) / 5 if len(candles) >= 5 else 0
    avg_late_vol = sum(c["volume"] for c in candles[-5:]) / 5 if len(candles) >= 5 else 0
    volume_ratio = (avg_late_vol / avg_early_vol) if avg_early_vol > 0 else 1.0

    return {
        "sector": sector,
        "ticker": ticker,
        "name": name,
        "trend": _label_trend(slope),
        "momentum_score": _momentum_score(slope, volume_ratio),
        "candles": candles,
        "ma5": _compute_ma(candles, 5),
        "ma20": ma20_values,
    }
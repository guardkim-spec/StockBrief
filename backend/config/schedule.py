"""KST-based schedule constants for the nightly pipeline."""

STEP_TIMES = {
    "korea_price":     "19:00",
    "korea_news":      "19:10",
    "us_price":        "19:20",
    "us_news":         "19:30",
    "gemini_analysis": "19:40",
    "trend_ai_global": "20:00",
    "charts_report":   "20:30",
    "storage":         "21:00",
    "email":           "21:30",
}

PIPELINE_STEPS = list(STEP_TIMES.keys())

OUTLIER_CHANGE_RATE_THRESHOLD = 30.0  # ±30% triggers outlier flag
TREND_UP_SLOPE_PCT = 2.0              # MA20 slope >= +2% → 우상향
TREND_DOWN_SLOPE_PCT = -2.0           # MA20 slope <= -2% → 우하향
CANDLE_DAYS = 20                      # days of candle history
TOP_N_STOCKS = 100                    # top N by trading volume
TOP_N_SECTORS_RECOMMEND = 3           # AI recommendation count

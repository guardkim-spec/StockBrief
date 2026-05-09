"""Generate chart images (base64 PNG) for email reports using matplotlib."""
import base64
import io
import logging
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

logger = logging.getLogger(__name__)

# Design system colors (from PRD §15)
BG_PRIMARY   = "#0D1117"
BG_SECONDARY = "#161B22"
BG_CARD      = "#1C2333"
COLOR_UP     = "#FF3B3B"
COLOR_DOWN   = "#3B8BFF"
COLOR_ACCENT = "#00FF88"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SEC     = "#8B949E"
BORDER       = "#30363D"


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=BG_CARD)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_sector_bar_chart(
    korea_scores: list[dict],
    us_scores: list[dict],
    title: str = "섹터 호재 점수",
) -> str:
    """Horizontal bar chart: top 8 sectors by score. Returns base64 PNG."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), facecolor=BG_CARD)
    fig.suptitle(title, color=TEXT_PRIMARY, fontsize=13, y=1.01)

    for ax, scores, label in [(ax1, korea_scores[:8], "한국"), (ax2, us_scores[:8], "미국")]:
        ax.set_facecolor(BG_CARD)
        if not scores:
            ax.text(0.5, 0.5, "데이터 없음", color=TEXT_SEC, ha="center", va="center", transform=ax.transAxes)
            continue

        sectors = [s["sector"] for s in reversed(scores)]
        values  = [s.get("score", s.get("avg_score", 0)) for s in reversed(scores)]
        colors  = [COLOR_UP if s.get("sentiment") == "positive" else COLOR_DOWN if s.get("sentiment") == "negative" else TEXT_SEC for s in reversed(scores)]

        bars = ax.barh(sectors, values, color=colors, height=0.6)
        ax.set_xlim(0, 11)
        ax.set_xlabel("점수", color=TEXT_SEC, fontsize=9)
        ax.set_title(label, color=TEXT_PRIMARY, fontsize=11)
        ax.tick_params(colors=TEXT_PRIMARY, labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.xaxis.label.set_color(TEXT_SEC)
        for bar, val in zip(bars, values):
            ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", color=TEXT_PRIMARY, fontsize=8)

    plt.tight_layout()
    return _fig_to_base64(fig)


def build_sector_pie_chart(volume_dist: list[dict], title: str = "거래대금 섹터 분포") -> str:
    """Pie chart for volume distribution. Returns base64 PNG."""
    if not volume_dist:
        fig, ax = plt.subplots(figsize=(6, 4), facecolor=BG_CARD)
        ax.text(0.5, 0.5, "데이터 없음", color=TEXT_SEC, ha="center", va="center")
        return _fig_to_base64(fig)

    colors = [
        "#FF3B3B","#3B8BFF","#00FF88","#FFD700","#FF69B4",
        "#00CED1","#FF8C00","#8B8BFF","#90EE90","#FFB6C1","#87CEEB","#DDA0DD",
    ]

    labels = [d["sector"] for d in volume_dist]
    sizes  = [d["ratio"] for d in volume_dist]
    clrs   = colors[:len(labels)]

    fig, ax = plt.subplots(figsize=(7, 5), facecolor=BG_CARD)
    ax.set_facecolor(BG_CARD)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=clrs,
        autopct="%1.1f%%", startangle=140,
        wedgeprops={"edgecolor": BG_CARD, "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_color(TEXT_PRIMARY)
        at.set_fontsize(8)

    ax.legend(
        wedges, labels,
        loc="lower right", fontsize=8,
        labelcolor=TEXT_PRIMARY,
        facecolor=BG_SECONDARY,
        edgecolor=BORDER,
    )
    ax.set_title(title, color=TEXT_PRIMARY, fontsize=12, pad=10)
    return _fig_to_base64(fig)


def build_candle_chart(candle_data: dict) -> str:
    """Simple candlestick chart with MA5/MA20 lines. Returns base64 PNG."""
    candles = candle_data.get("candles", [])
    if not candles:
        fig, ax = plt.subplots(figsize=(8, 4), facecolor=BG_CARD)
        ax.text(0.5, 0.5, "캔들 데이터 없음", color=TEXT_SEC, ha="center", va="center")
        return _fig_to_base64(fig)

    dates   = list(range(len(candles)))
    opens   = [c["open"] for c in candles]
    highs   = [c["high"] for c in candles]
    lows    = [c["low"]  for c in candles]
    closes  = [c["close"] for c in candles]

    fig, ax = plt.subplots(figsize=(10, 4), facecolor=BG_CARD)
    ax.set_facecolor(BG_CARD)

    for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
        color = COLOR_UP if c >= o else COLOR_DOWN
        ax.plot([i, i], [l, h], color=color, linewidth=0.8)
        ax.add_patch(
            plt.Rectangle(
                (i - 0.3, min(o, c)), 0.6, abs(c - o) or 1,
                color=color, alpha=0.9,
            )
        )

    # MA lines
    ma5  = candle_data.get("ma5",  [])
    ma20 = candle_data.get("ma20", [])
    offset5  = len(candles) - len(ma5)
    offset20 = len(candles) - len(ma20)
    if ma5:
        ax.plot([offset5 + i for i in range(len(ma5))], [m["value"] for m in ma5],
                color="#FFD700", linewidth=1.2, label="MA5")
    if ma20:
        ax.plot([offset20 + i for i in range(len(ma20))], [m["value"] for m in ma20],
                color=COLOR_ACCENT, linewidth=1.5, label="MA20")

    # X-axis date labels (every 5)
    step = max(1, len(candles) // 5)
    ax.set_xticks(dates[::step])
    ax.set_xticklabels([candles[i]["date"][5:] for i in dates[::step]], rotation=30, fontsize=7)

    sector = candle_data.get("sector", "")
    name   = candle_data.get("name",   "")
    trend  = candle_data.get("trend",  "")
    score  = candle_data.get("momentum_score", "")
    ax.set_title(f"{sector} | {name}  [{trend}] 모멘텀:{score}", color=TEXT_PRIMARY, fontsize=11)
    ax.tick_params(colors=TEXT_PRIMARY, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.legend(fontsize=8, facecolor=BG_SECONDARY, labelcolor=TEXT_PRIMARY, edgecolor=BORDER)
    ax.yaxis.set_tick_params(labelcolor=TEXT_PRIMARY)

    plt.tight_layout()
    return _fig_to_base64(fig)
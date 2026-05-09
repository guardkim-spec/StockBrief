"""Compose HTML email report."""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def build_email_html(
    date_str: str,
    ai_recommendation: dict,
    korea_sector_ranking: list[dict],
    us_sector_ranking: list[dict],
    korea_volume_dist: list[dict],
    candle_data: list[dict],
    global_summary: str,
    chart_bar_b64: str,
    chart_pie_b64: str,
    chart_candles: list[str],
) -> str:
    """Build full HTML email string."""
    summary_lines = _build_summary(ai_recommendation, korea_sector_ranking)
    sectors_html  = _render_sector_table(korea_sector_ranking, "한국 섹터 점수")
    us_html       = _render_sector_table(us_sector_ranking,   "미국 섹터 점수")
    candle_html   = _render_candle_charts(candle_data, chart_candles)

    rec_sectors = "·".join(ai_recommendation.get("sectors", []))
    rec_reason  = ai_recommendation.get("reason", "")
    confidence  = ai_recommendation.get("confidence", 0)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>StockBrief {date_str}</title>
<style>
  body {{background:#0D1117;color:#ffffff;font-family:'Pretendard','Apple SD Gothic Neo',sans-serif;margin:0;padding:20px;}}
  .container {{max-width:800px;margin:0 auto;}}
  .header {{text-align:center;border-bottom:1px solid #30363D;padding-bottom:16px;margin-bottom:24px;}}
  .header h1 {{color:#00FF88;font-size:22px;margin:0;}}
  .header p  {{color:#8B949E;font-size:12px;margin:4px 0 0;}}
  .card {{background:#1C2333;border:1px solid #30363D;border-radius:12px;padding:20px;margin-bottom:20px;}}
  .card h2 {{color:#00FF88;font-size:14px;margin:0 0 12px;text-transform:uppercase;letter-spacing:1px;}}
  .summary-lines {{list-style:none;padding:0;margin:0;}}
  .summary-lines li {{padding:6px 0;border-bottom:1px solid #30363D;font-size:13px;color:#c9d1d9;}}
  .summary-lines li:last-child {{border-bottom:none;}}
  .rec-box {{background:#161B22;border:1px solid #00FF88;border-radius:8px;padding:12px;}}
  .rec-sectors {{font-size:18px;font-weight:bold;color:#00FF88;margin:0 0 8px;}}
  .rec-reason  {{font-size:12px;color:#8B949E;line-height:1.6;}}
  .confidence  {{font-size:11px;color:#FFD700;margin-top:6px;}}
  .chart-img   {{width:100%;border-radius:8px;margin-top:8px;}}
  table {{width:100%;border-collapse:collapse;font-size:12px;}}
  th {{background:#161B22;color:#8B949E;text-align:left;padding:8px;}}
  td {{padding:7px 8px;border-bottom:1px solid #30363D;color:#c9d1d9;}}
  tr:nth-child(even) td {{background:#161B22;}}
  .pos {{color:#FF3B3B;}} .neg {{color:#3B8BFF;}} .neu {{color:#8B949E;}}
  .footer {{text-align:center;color:#8B949E;font-size:11px;margin-top:32px;padding-top:16px;border-top:1px solid #30363D;}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📊 StockBrief</h1>
    <p>{date_str} · 매일 오후 9시 30분 발송</p>
  </div>

  <div class="card">
    <h2>핵심 요약</h2>
    <ul class="summary-lines">
      {"".join(f"<li>{line}</li>" for line in summary_lines)}
    </ul>
  </div>

  <div class="card">
    <h2>🤖 AI 추천 — 내일 주목 섹터</h2>
    <div class="rec-box">
      <div class="rec-sectors">{rec_sectors}</div>
      <div class="rec-reason">{rec_reason}</div>
      <div class="confidence">신뢰도 {confidence:.0%}</div>
    </div>
  </div>

  <div class="card">
    <h2>섹터 호재 랭킹</h2>
    <img class="chart-img" src="data:image/png;base64,{chart_bar_b64}" alt="섹터 호재 랭킹">
  </div>

  <div class="card">
    <h2>거래대금 섹터 분포</h2>
    <img class="chart-img" src="data:image/png;base64,{chart_pie_b64}" alt="거래대금 분포">
  </div>

  {candle_html}

  <div class="card">
    <h2>한미 연계 분석</h2>
    <p style="font-size:13px;line-height:1.7;color:#c9d1d9;">{global_summary}</p>
  </div>

  {sectors_html}
  {us_html}

  <div class="footer">
    <p>이 리포트는 투자 추천이 아닌 정보 제공 목적으로 제공됩니다.</p>
    <p>StockBrief v2.0 · Powered by Gemini 1.5 Flash</p>
  </div>
</div>
</body>
</html>"""


def _build_summary(rec: dict, korea_ranking: list[dict]) -> list[str]:
    top_sectors = rec.get("sectors", [])
    lines = []
    if top_sectors:
        lines.append(f"내일 주목 섹터: {', '.join(top_sectors[:3])} (AI 추천)")
    if korea_ranking:
        top = korea_ranking[0]
        lines.append(f"한국 최고 섹터: {top['sector']} (점수 {top['score']:.1f})")
    if rec.get("reason"):
        brief = rec["reason"]
        lines.append(brief)
    return lines or ["오늘 분석 데이터를 확인하세요."]


def _render_sector_table(rankings: list[dict], title: str) -> str:
    # Filter out the catch-all "기타" sector — it's just unanalyzed noise
    filtered = [r for r in rankings if r.get("sector") != "기타"]
    if not filtered:
        return f"""<div class="card">
    <h2>{title}</h2>
    <p style="color:#8B949E;font-size:13px;margin:0;">섹터 분석 데이터 없음 (뉴스 부족 또는 Gemini 할당량 초과)</p>
  </div>"""
    rows = ""
    for item in filtered[:12]:
        sent = item.get("sentiment", "neutral")
        cls  = "pos" if sent == "positive" else ("neg" if sent == "negative" else "neu")
        label = "▲" if sent == "positive" else ("▼" if sent == "negative" else "—")
        rows += f"<tr><td>{item['sector']}</td><td>{item.get('score', 0):.1f}</td><td class='{cls}'>{label}</td></tr>"
    return f"""<div class="card">
    <h2>{title}</h2>
    <table><tr><th>섹터</th><th>점수</th><th>방향</th></tr>{rows}</table>
  </div>"""


def _render_candle_charts(candle_data: list[dict], charts_b64: list[str]) -> str:
    html = ""
    for candle, b64 in zip(candle_data, charts_b64):
        sector = candle.get("sector", "")
        trend  = candle.get("trend", "")
        score  = candle.get("momentum_score", "")
        html += f"""<div class="card">
    <h2>{sector} 캔들차트 [{trend}] 모멘텀 {score}</h2>
    <img class="chart-img" src="data:image/png;base64,{b64}" alt="{sector} 캔들">
  </div>"""
    return html
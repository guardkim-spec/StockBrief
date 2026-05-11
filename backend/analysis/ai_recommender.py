"""AI sector recommendation using Gemini."""
import json
import logging
from typing import Any

from analysis.gemini_client import call_gemini_json
from config.schedule import TOP_N_SECTORS_RECOMMEND

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """
당신은 한국 주식 시장 전문 분석가입니다. 아래 데이터를 종합하여 내일 주목해야 할 섹터 상위 {n}개를 추천하세요.

## 오늘 한국 섹터 뉴스 점수 (높을수록 호재)
{korea_news_scores}

## 오늘 미국 섹터 뉴스 점수
{us_news_scores}

## 거래대금 상위 섹터 (한국)
{korea_volume}

## 주목 섹터 추세 분석
{trend_data}

## 과거 AI 추천 정확도
{backtest_summary}

다음 JSON 형식으로만 응답하세요:
{{
  "sectors": ["섹터1", "섹터2", "섹터3"],
  "reason": "추천 근거 텍스트 (200자 이내)",
  "confidence": 0.0~1.0 사이 숫자
}}
"""


def recommend_sectors(
    korea_news_scores: list[dict],
    us_news_scores: list[dict],
    korea_volume: list[dict],
    trend_data: list[dict],
    backtest_records: list[dict],
) -> dict[str, Any]:
    """Generate AI sector recommendation."""
    backtest_summary = _summarize_backtest(backtest_records)

    prompt = _PROMPT_TEMPLATE.format(
        n=TOP_N_SECTORS_RECOMMEND,
        korea_news_scores=json.dumps(korea_news_scores[:8], ensure_ascii=False),
        us_news_scores=json.dumps(us_news_scores[:8], ensure_ascii=False),
        korea_volume=json.dumps(korea_volume[:8], ensure_ascii=False),
        trend_data=json.dumps([{"sector": t["sector"], "trend": t["trend"], "momentum_score": t["momentum_score"]} for t in trend_data], ensure_ascii=False),
        backtest_summary=backtest_summary,
    )

    result = call_gemini_json(prompt, cache_key="ai_recommendation")

    if not result or "sectors" not in result:
        logger.warning("Gemini recommendation failed; using score-based fallback")
        return _fallback_recommendation(korea_news_scores, korea_volume)

    # Filter out catch-all '기타' — it's unsectored noise, not a real recommendation
    valid_sectors = [s for s in result.get("sectors", []) if s and s != "기타"]
    return {
        "sectors": valid_sectors[:TOP_N_SECTORS_RECOMMEND],
        "reason": result.get("reason", ""),
        "confidence": float(result.get("confidence", 0.5)),
    }


def _summarize_backtest(records: list[dict]) -> str:
    if not records:
        return "백테스팅 데이터 없음"
    recent = records[:10]
    avg_acc = sum(r.get("accuracy", 0) for r in recent) / len(recent)
    return f"최근 {len(recent)}일 평균 정확도: {avg_acc:.1%}"


def _fallback_recommendation(news_scores: list[dict], volume_dist: list[dict]) -> dict[str, Any]:
    """Score-based fallback when Gemini is unavailable."""
    combined: dict[str, float] = {}
    for item in news_scores:
        sector = item.get("sector", "")
        if not sector or sector == "기타":
            continue
        combined[sector] = combined.get(sector, 0) + item.get("avg_score", 0) * 0.6
    for item in volume_dist:
        sector = item.get("sector", "")
        if not sector or sector == "기타":
            continue
        combined[sector] = combined.get(sector, 0) + item.get("ratio", 0) * 100 * 0.4

    top = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:TOP_N_SECTORS_RECOMMEND]
    return {
        "sectors": [s for s, _ in top],
        "reason": "뉴스 점수와 거래대금 비중 기반 자동 선정 (Gemini 대체)",
        "confidence": 0.5,
    }
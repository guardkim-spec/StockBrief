"""Korea-US linkage analysis using Gemini."""
import json
import logging
from typing import Any

from analysis.gemini_client import call_gemini_json
from config.sectors import get_sector_list

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """
당신은 한미 주식 시장 연계 분석 전문가입니다.
미국 섹터별 뉴스/시세 동향이 다음날 한국 시장에 미칠 영향을 분석해 주세요.

## 미국 섹터 현황
{us_sector_data}

## 한국 섹터 현황
{korea_sector_data}

## 공통 섹터 매핑
{sector_mapping}

각 연관 섹터 쌍에 대해 다음 JSON 형식으로 응답하세요 (배열):
[
  {{
    "us_sector": "섹터명",
    "us_sentiment": "positive|neutral|negative",
    "us_score": 0~10,
    "korea_sector": "섹터명",
    "predicted_impact": "positive|neutral|negative",
    "impact_strength": 0.0~1.0,
    "summary": "한 줄 요약 (100자 이내)",
    "reasoning": "분석 근거 (200자 이내)"
  }}
]
그리고 마지막에 "overall_summary" 키를 포함한 전체 분석 텍스트를 추가하세요.
"""


def analyze_global_linkage(
    us_sector_scores: list[dict],
    korea_sector_scores: list[dict],
) -> dict[str, Any]:
    """Generate Korea-US sector linkage analysis."""
    sectors = get_sector_list()
    sector_mapping = {s: s for s in sectors}  # 1:1 mapping for common sectors

    prompt = _PROMPT_TEMPLATE.format(
        us_sector_data=json.dumps(us_sector_scores[:8], ensure_ascii=False),
        korea_sector_data=json.dumps(korea_sector_scores[:8], ensure_ascii=False),
        sector_mapping=json.dumps(sector_mapping, ensure_ascii=False),
    )

    result = call_gemini_json(prompt, cache_key="global_linkage")

    if not result:
        logger.warning("Gemini global linkage failed; using rule-based fallback")
        return _fallback_linkage(us_sector_scores, korea_sector_scores)

    # Gemini may return list or dict
    if isinstance(result, list):
        cards = result
        overall = ""
    elif isinstance(result, dict):
        cards = result.get("linkage_cards", result.get("cards", []))
        overall = result.get("overall_summary", "")
    else:
        return _fallback_linkage(us_sector_scores, korea_sector_scores)

    return {
        "linkage_cards": cards,
        "gemini_overall_summary": overall,
    }


def _fallback_linkage(us_scores: list[dict], korea_scores: list[dict]) -> dict[str, Any]:
    """Rule-based fallback: map same sector names, infer impact from sentiment."""
    korea_map = {item["sector"]: item for item in korea_scores}
    cards = []
    for us in us_scores[:5]:
        sector = us["sector"]
        kr = korea_map.get(sector, {})
        cards.append({
            "us_sector": sector,
            "us_sentiment": us.get("sentiment", "neutral"),
            "us_score": us.get("score", 5),
            "korea_sector": sector,
            "predicted_impact": us.get("sentiment", "neutral"),
            "impact_strength": 0.6,
            "summary": f"미국 {sector} 동향이 한국 {sector} 섹터에 영향을 줄 수 있습니다.",
            "reasoning": "동일 섹터 글로벌 공급망 연계 (Gemini 대체)",
        })
    return {
        "linkage_cards": cards,
        "gemini_overall_summary": "Gemini API 미사용 — 규칙 기반 연계 분석 결과입니다.",
    }
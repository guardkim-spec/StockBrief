"""Thin wrapper around Google Gemini API with quota handling."""
import json
import logging
from typing import Any

from google import genai
from google.genai import types

from config.settings import settings
from pipeline.retry import retry

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-2.5-flash"
_MAX_TOKENS = 16384
_LAST_RESULT_CACHE: dict[str, Any] = {}


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


@retry(max_attempts=3, delay_sec=30.0, exceptions=(Exception,))
def call_gemini(prompt: str, cache_key: str = "", json_mode: bool = False) -> str:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set; returning empty response")
        return _LAST_RESULT_CACHE.get(cache_key, "")

    try:
        client = _get_client()
        config_kwargs: dict = {"max_output_tokens": _MAX_TOKENS, "temperature": 0.3}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        result = response.text.strip()
        if cache_key:
            _LAST_RESULT_CACHE[cache_key] = result
        return result
    except Exception as exc:
        error_str = str(exc).lower()
        if "quota" in error_str or "429" in error_str or "resource_exhausted" in error_str:
            logger.warning("Gemini quota exceeded. Using cached result for key: %s", cache_key)
            if cache_key and cache_key in _LAST_RESULT_CACHE:
                return _LAST_RESULT_CACHE[cache_key]
            return ""
        if "404" in error_str or "not_found" in error_str:
            logger.error("Gemini model not found: %s — check _MODEL_NAME in gemini_client.py", exc)
            return ""
        raise


def call_gemini_json(prompt: str, cache_key: str = "") -> dict | list:
    """Call Gemini in JSON mode (response_mime_type=application/json). Returns empty dict on failure."""
    raw = call_gemini(prompt, cache_key, json_mode=True)
    if not raw:
        return {}
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        logger.warning("Gemini JSON parse error: %s — raw: %.200s", exc, raw)
        return {}

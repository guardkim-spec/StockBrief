import json
from pathlib import Path
from functools import lru_cache

_SECTORS_FILE = Path(__file__).resolve().parent.parent.parent / "shared" / "sectors.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(_SECTORS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_sector_list() -> list[str]:
    return _load()["sectors"]


def get_korea_ticker_map() -> dict[str, str]:
    return _load()["korea_ticker_map"]


def get_us_gics_sector_map() -> dict[str, str]:
    return _load()["us_gics_sector_map"]


def get_us_ticker_override() -> dict[str, str]:
    return _load()["us_ticker_sector_override"]


def classify_korea_ticker(ticker: str) -> str:
    return get_korea_ticker_map().get(ticker, "기타")


def classify_us_ticker(ticker: str, gics_sector: str = "") -> str:
    override = get_us_ticker_override()
    if ticker in override:
        return override[ticker]
    gics_map = get_us_gics_sector_map()
    return gics_map.get(gics_sector, "기타")

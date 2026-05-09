
from fastapi import APIRouter, Query
from ._helpers import _read_data_file, today_str

router = APIRouter()


@router.get("/news")
def get_news(market: str = Query("korea", pattern="^(korea|us)$"), date: str | None = None):
    d = date or today_str()
    filename = f"{market}_news.json"
    data = _read_data_file(d, filename)
    if data:
        return data
    # fallback: generic news mock
    from ._helpers import _read_mock
    mock = _read_mock("news.json")
    mock["data"]["market"] = market
    return mock

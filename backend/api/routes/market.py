
from fastapi import APIRouter, Query
from ._helpers import _read_data_file, today_str

router = APIRouter()


@router.get("/market")
def get_market(market: str = Query("korea", pattern="^(korea|us)$"), date: str | None = None):
    d = date or today_str()
    filename = f"{market}_price.json"
    data = _read_data_file(d, filename)
    if data:
        candle_data = _read_data_file(d, "candle_data.json")
        if candle_data:
            data["data"]["candle_data"] = candle_data.get("data", {}).get("candle_data", [])
        return data
    from ._helpers import _read_mock
    mock = _read_mock("market.json")
    mock["data"]["market"] = market
    return mock

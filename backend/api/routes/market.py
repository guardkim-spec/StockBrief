
from fastapi import APIRouter, Query
from ._helpers import _read_data_file, today_str

router = APIRouter()


@router.get("/market")
def get_market(market: str = Query("korea", pattern="^(korea|us)$"), date: str | None = None):
    d = date or today_str()
    filename = f"{market}_price.json"
    price_raw = _read_data_file(d, filename)
    if price_raw:
        candle_list = []
        if market == "korea":
            candle_file = _read_data_file(d, "candle_data.json")
            candle_list = candle_file.get("data", {}).get("candle_data", []) if candle_file else []
        return {
            "ok": True,
            "date": d,
            "data": {
                "market": market,
                "date": d,
                "top100": price_raw.get("data", []),
                "candle_data": candle_list,
            },
        }
    from ._helpers import _read_mock
    mock = _read_mock("market.json")
    mock["data"]["market"] = market
    return mock

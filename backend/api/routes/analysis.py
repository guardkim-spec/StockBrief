from fastapi import APIRouter
from ._helpers import _read_data_file, today_str, _read_mock

router = APIRouter()


@router.get("/analysis")
def get_analysis(date: str | None = None):
    d = date or today_str()
    raw = _read_data_file(d, "analysis.json")

    if raw:
        data = raw.get("data", [])
        # Handle both old flat-array format and new dict format
        records = data if isinstance(data, list) else data.get("records", [])
    else:
        mock = _read_mock("analysis.json")
        records = mock.get("data", [])

    # Enrich with US sector ranking from dashboard (served at request time)
    us_ranking = []
    dashboard = _read_data_file(d, "dashboard.json")
    if dashboard:
        us_ranking = dashboard.get("data", {}).get("us_sector_ranking", [])

    return {
        "ok": True,
        "date": d,
        "data": {
            "records": records,
            "us_ranking": us_ranking,
        },
    }

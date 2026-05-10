
from fastapi import APIRouter
from ._helpers import _read_data_file, today_str, _read_mock

router = APIRouter()


@router.get("/analysis")
def get_analysis(date: str | None = None):
    d = date or today_str()
    data = _read_data_file(d, "analysis.json")
    if data:
        return data
    return _read_mock("analysis.json")


from fastapi import APIRouter
from ._helpers import _read_data_file, today_str

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(date: str | None = None):
    d = date or today_str()
    data = _read_data_file(d, "dashboard.json")
    if data:
        return data
    from ._helpers import _read_mock
    return _read_mock("dashboard.json")

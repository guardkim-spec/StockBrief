
from fastapi import APIRouter
from ._helpers import _read_data_file, today_str

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(date: str | None = None):
    d = date or today_str()
    data = _read_data_file(d, "dashboard.json")
    if data:
        return data
    return {"ok": False, "error": "PIPELINE_NOT_RUN", "message": "오늘 데이터를 준비 중입니다", "last_success_date": None}

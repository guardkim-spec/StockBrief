
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ._helpers import _read_data_file, today_str, _read_mock

router = APIRouter()


class ResendRequest(BaseModel):
    date: str | None = None


@router.get("/report")
def get_report(date: str | None = None):
    d = date or today_str()
    data = _read_data_file(d, "report.json")
    if data:
        return data
    return _read_mock("report.json")


@router.post("/report/resend")
def resend_report(body: ResendRequest):
    from pipeline.orchestrator import queue_resend
    d = body.date or today_str()
    try:
        queue_resend(d)
        return {"ok": True, "data": {"queued": True, "message": "재발송 요청이 접수되었습니다.", "date": d}}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

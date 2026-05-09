
from fastapi import APIRouter
from ._helpers import _read_data_file, today_str, _read_mock

router = APIRouter()


@router.get("/pipeline/status")
def get_pipeline_status():
    d = today_str()
    data = _read_data_file(d, "pipeline-status.json")
    if data:
        return data
    return _read_mock("pipeline-status.json")

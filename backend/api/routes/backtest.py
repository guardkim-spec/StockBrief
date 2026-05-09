
from fastapi import APIRouter, Query
import json
from pathlib import Path
from config.settings import settings
from ._helpers import today_str

router = APIRouter()


@router.get("/backtest")
def get_backtest(limit: int = Query(30, ge=1, le=365)):
    # Collect all available backtest records from data/YYYY-MM-DD/backtest.json
    records = []
    data_dir = settings.data_dir
    if data_dir.exists():
        for date_dir in sorted(data_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            bt_file = date_dir / "backtest.json"
            if bt_file.exists():
                try:
                    with open(bt_file, encoding="utf-8") as f:
                        bt = json.load(f)
                    rec = bt.get("data", bt)
                    if isinstance(rec, dict) and "date" in rec:
                        records.append(rec)
                except Exception:
                    pass
            if len(records) >= limit:
                break

    if not records:
        # fallback to mock
        mock_path = settings.mock_data_dir / "backtest.json"
        with open(mock_path, encoding="utf-8") as f:
            return json.load(f)

    cumulative = sum(r.get("accuracy", 0) for r in records) / len(records) if records else 0
    return {"ok": True, "date": today_str(), "data": {"cumulative_accuracy": round(cumulative, 4), "records": records[:limit]}}

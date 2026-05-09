"""Google Sheets read/write client with duplicate prevention."""
import json
import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_TAB_COLUMNS = {
    "korea_price": ["date","ticker","name","market","sector","volume_amount","change_rate","rank","is_outlier"],
    "us_price":    ["date","ticker","name","market","sector","volume_amount","change_rate","rank","is_outlier"],
    "korea_news":  ["date","id","title","url","source","sector","sentiment","score"],
    "us_news":     ["date","id","title","url","source","sector","sentiment","score"],
    "analysis":    ["date","sector","news_score","volume_score","trend_score","total_score","recommendation","confidence"],
    "backtest":    ["date","recommended_sectors","actual_top_sectors","accuracy","hit_sectors","miss_sectors"],
    "pipeline_log":["date","step","status","ran_at","duration_sec","error_message"],
}

# Dedup keys: (tab -> list of column names that together form unique key)
_DEDUP_KEYS = {
    "korea_price": ["date", "ticker"],
    "us_price":    ["date", "ticker"],
    "korea_news":  ["date", "id"],
    "us_news":     ["date", "id"],
    "analysis":    ["date", "sector"],
    "backtest":    ["date"],
    "pipeline_log":["date", "step"],
}


def _get_client() -> gspread.Client:
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    creds_dict = json.loads(settings.google_service_account_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _ensure_tab(spreadsheet: gspread.Spreadsheet, tab_name: str) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        cols = _TAB_COLUMNS.get(tab_name, [])
        ws = spreadsheet.add_worksheet(title=tab_name, rows=10000, cols=len(cols) or 20)
        if cols:
            ws.append_row(cols)
    return ws


def append_rows(tab_name: str, rows: list[dict[str, Any]]) -> int:
    """Append rows to a Sheets tab, skipping duplicates. Returns count of inserted rows."""
    if not rows:
        return 0

    gc = _get_client()
    spreadsheet = gc.open_by_key(settings.google_sheets_id)
    ws = _ensure_tab(spreadsheet, tab_name)

    columns = _TAB_COLUMNS.get(tab_name, list(rows[0].keys()))
    dedup_keys = _DEDUP_KEYS.get(tab_name, [])

    # Load existing dedup key set
    existing_keys: set[str] = set()
    if dedup_keys:
        try:
            existing = ws.get_all_records()
            for record in existing:
                key = "|".join(str(record.get(k, "")) for k in dedup_keys)
                existing_keys.add(key)
        except Exception as exc:
            logger.warning("Could not load existing records for dedup: %s", exc)

    inserted = 0
    for row in rows:
        if dedup_keys:
            key = "|".join(str(row.get(k, "")) for k in dedup_keys)
            if key in existing_keys:
                continue
            existing_keys.add(key)

        values = []
        for col in columns:
            v = row.get(col, "")
            if isinstance(v, (list, dict, bool)):
                v = json.dumps(v, ensure_ascii=False)
            values.append(v)

        ws.append_row(values)
        inserted += 1

    logger.info("Sheets tab %s: inserted %d/%d rows", tab_name, inserted, len(rows))
    return inserted
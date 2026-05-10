"""Nightly pipeline orchestrator -runs all 9 steps in order."""
import json
import logging
import threading
from datetime import datetime
from typing import Any

import pytz

from config.settings import settings
from config.schedule import PIPELINE_STEPS
from pipeline.notifier import notify_step_failure, notify_pipeline_success, notify_holiday

logger = logging.getLogger(__name__)
KST = pytz.timezone("Asia/Seoul")

_resend_queue: list[str] = []
_resend_lock = threading.Lock()


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _is_holiday(date_str: str) -> tuple[bool, str]:
    import holidays as hols
    from datetime import date as dt_date
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    kr = hols.country_holidays("KR", years=d.year)
    us = hols.country_holidays("US", years=d.year)
    if d in kr:
        return True, "한국"
    if d in us:
        return True, "미국"
    if d.weekday() >= 5:
        return True, "주말"
    return False, ""


def _make_step(name: str, status: str = "pending") -> dict:
    return {"name": name, "status": status, "ran_at": None, "duration_sec": None}


def _start_step(step: dict) -> None:
    step["status"] = "running"
    step["ran_at"] = datetime.now(KST).isoformat()


def _finish_step(step: dict, start_ts: float, success: bool) -> None:
    import time
    step["status"] = "success" if success else "failed"
    step["duration_sec"] = round(time.time() - start_ts, 1)


def run_pipeline(date_str: str | None = None, dry_run: bool = False) -> bool:
    """Run full nightly pipeline. Returns True if all steps succeeded."""
    import time
    date_str = date_str or _today()
    logger.info("=== StockBrief Pipeline START: %s (dry_run=%s) ===", date_str, dry_run)

    is_hol, market = _is_holiday(date_str)
    if is_hol:
        logger.info("Holiday detected: %s. Sending holiday notification.", market)
        if not dry_run:
            notify_holiday(date_str, market)
        return True

    steps = [_make_step(name) for name in PIPELINE_STEPS]
    step_map = {s["name"]: s for s in steps}

    def update_status():
        if not dry_run:
            from storage.github_storage import save_pipeline_status
            try:
                save_pipeline_status(date_str, steps)
            except Exception as exc:
                logger.warning("Could not update pipeline status: %s", exc)

    # Collected data across steps
    ctx: dict[str, Any] = {"date": date_str}

    def run_step(name: str, fn, *args, **kwargs):
        step = step_map[name]
        _start_step(step)
        update_status()
        t0 = time.time()
        try:
            if not dry_run:
                result = fn(*args, **kwargs)
            else:
                logger.info("[dry_run] skipping %s", name)
                result = None
            _finish_step(step, t0, True)
            update_status()
            return result
        except Exception as exc:
            _finish_step(step, t0, False)
            update_status()
            logger.error("Step %s FAILED: %s", name, exc)
            notify_step_failure(name, exc)
            return None

    # ── Step 1: Korea price ──────────────────────────────────────────
    from collectors.korea_price import collect_korea_top100
    ctx["korea_price"] = run_step("korea_price", collect_korea_top100, date_str) or []

    # ── Step 2: Korea news ───────────────────────────────────────────
    from collectors.korea_news import collect_korea_news
    from analysis.gemini_client import call_gemini_json
    raw_korea_news = run_step("korea_news", collect_korea_news, date_str) or []
    ctx["korea_news"] = _analyze_news(raw_korea_news, "ko", dry_run)

    # ── Step 3: US price ─────────────────────────────────────────────
    import os as _os
    if _os.getenv("SKIP_US_PRICE", "").lower() == "true":
        logger.info("US price collection skipped (SKIP_US_PRICE=true)")
        ctx["us_price"] = []
        step_map["us_price"]["status"] = "skipped"
        step_map["us_price"]["ran_at"] = datetime.now(KST).isoformat()
        step_map["us_price"]["duration_sec"] = 0
        update_status()
    else:
        from collectors.us_price import collect_us_top100
        ctx["us_price"] = run_step("us_price", collect_us_top100, date_str) or []

    # ── Step 4: US news ──────────────────────────────────────────────
    from collectors.us_news import collect_us_news
    raw_us_news = run_step("us_news", collect_us_news, date_str) or []
    ctx["us_news"] = _analyze_news(raw_us_news, "en", dry_run)

    # ── Step 5: Gemini sector analysis ───────────────────────────────
    from analysis.sector_classifier import aggregate_sector_volume, aggregate_sector_news_scores
    ctx["korea_volume_dist"] = aggregate_sector_volume(ctx["korea_price"])
    ctx["us_volume_dist"]    = aggregate_sector_volume(ctx["us_price"])
    ctx["korea_news_scores"] = aggregate_sector_news_scores(ctx["korea_news"])
    ctx["us_news_scores"]    = aggregate_sector_news_scores(ctx["us_news"])
    step_map["gemini_analysis"]["status"] = "success"
    step_map["gemini_analysis"]["ran_at"] = datetime.now(KST).isoformat()
    step_map["gemini_analysis"]["duration_sec"] = 0
    update_status()

    # ── Step 6: Trend + AI recommendation + Korea-US linkage ─────────
    from analysis.trend_analyzer import analyze_sector_trend
    from analysis.ai_recommender import recommend_sectors
    from analysis.global_linker  import analyze_global_linkage

    top_sectors = [item["sector"] for item in sorted(ctx["korea_news_scores"], key=lambda x: x["avg_score"], reverse=True)[:3]]

    def _run_trend_ai_global():
        sector_tickers = _get_representative_tickers(ctx["korea_price"], top_sectors)
        trend_data = []
        for sector, ticker, name in sector_tickers:
            trend = analyze_sector_trend(sector, ticker, name, "korea")
            trend_data.append(trend)
        ctx["candle_data"] = trend_data

        backtest = _load_backtest(date_str)
        ctx["ai_recommendation"] = recommend_sectors(
            ctx["korea_news_scores"], ctx["us_news_scores"],
            ctx["korea_volume_dist"], trend_data, backtest,
        )
        ctx["global_linkage"] = analyze_global_linkage(
            ctx["us_news_scores"], ctx["korea_news_scores"]
        )

    run_step("trend_ai_global", _run_trend_ai_global)

    # ── Step 7: Charts + Report HTML ─────────────────────────────────
    from report.chart_builder import build_sector_bar_chart, build_sector_pie_chart, build_candle_chart
    from report.html_builder  import build_email_html

    def _build_charts_report():
        bar_b64  = build_sector_bar_chart(ctx["korea_news_scores"], ctx["us_news_scores"])
        pie_b64  = build_sector_pie_chart(ctx["korea_volume_dist"])
        candle_b64s = [build_candle_chart(c) for c in ctx.get("candle_data", [])]

        global_summary = ctx.get("global_linkage", {}).get("gemini_overall_summary", "")
        html = build_email_html(
            date_str=date_str,
            ai_recommendation=ctx.get("ai_recommendation", {}),
            korea_sector_ranking=_to_ranking(ctx["korea_news_scores"]),
            us_sector_ranking=_to_ranking(ctx["us_news_scores"]),
            korea_volume_dist=ctx["korea_volume_dist"],
            candle_data=ctx.get("candle_data", []),
            global_summary=global_summary,
            chart_bar_b64=bar_b64,
            chart_pie_b64=pie_b64,
            chart_candles=candle_b64s,
        )
        ctx["report_html"] = html

    run_step("charts_report", _build_charts_report)

    # ── Step 8: Storage ───────────────────────────────────────────────
    def _save_all():
        from storage.github_storage import save_daily_file, save_latest
        from storage.sheets_client  import append_rows

        save_daily_file(date_str, "korea_price.json",   _wrap(date_str, ctx["korea_price"]))
        save_daily_file(date_str, "us_price.json",       _wrap(date_str, ctx["us_price"]))
        save_daily_file(date_str, "korea_news.json",     _wrap(date_str, ctx["korea_news"]))
        save_daily_file(date_str, "us_news.json",        _wrap(date_str, ctx["us_news"]))
        save_daily_file(date_str, "analysis.json",       _build_analysis_payload(date_str, ctx))
        save_daily_file(date_str, "candle_data.json",    _wrap(date_str, {"candle_data": ctx.get("candle_data", [])}))
        save_daily_file(date_str, "global.json",         _build_global_payload(date_str, ctx))
        save_daily_file(date_str, "pipeline-status.json",{"ok":True,"date":date_str,"data":{"date":date_str,"overall":"success","steps":steps}})

        if ctx.get("report_html"):
            # Drive upload skipped: Service Accounts have no storage quota on regular Drive.
            # HTML is persisted in report.json (html_content) and report.html locally.
            report_payload = _build_report_payload(date_str, ctx, "")
            save_daily_file(date_str, "report.json", report_payload)
            report_html_path = settings.data_dir / date_str / "report.html"
            report_html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_html_path, "w", encoding="utf-8") as fh:
                fh.write(ctx["report_html"])

        dashboard_payload = _build_dashboard_payload(date_str, ctx)
        save_latest(dashboard_payload)
        save_daily_file(date_str, "dashboard.json", dashboard_payload)

        backtest_record = _build_backtest_record(date_str, ctx)
        if backtest_record:
            save_daily_file(date_str, "backtest.json", _wrap(date_str, backtest_record))

        try:
            append_rows("korea_price", ctx["korea_price"])
            append_rows("us_price",    ctx["us_price"])
            append_rows("korea_news",  ctx["korea_news"])
            append_rows("us_news",     ctx["us_news"])
        except Exception as exc:
            logger.warning("Sheets append_rows failed (non-fatal): %s", exc)

    run_step("storage", _save_all)

    # ── Step 9: Email ─────────────────────────────────────────────────
    from report.email_sender import send_report

    def _send_email():
        if not ctx.get("report_html"):
            raise RuntimeError("No report HTML to send")
        success = send_report(date_str, ctx["report_html"])
        if not success:
            raise RuntimeError("Email send returned False")

    run_step("email", _send_email)

    all_ok = all(s["status"] in ("success", "skipped") for s in steps)
    if all_ok:
        notify_pipeline_success(date_str)
        logger.info("=== Pipeline COMPLETE: %s ===", date_str)
    else:
        failed = [s["name"] for s in steps if s["status"] == "failed"]
        logger.error("=== Pipeline PARTIAL FAILURE: %s -failed: %s ===", date_str, failed)

    return all_ok


def queue_resend(date_str: str) -> None:
    with _resend_lock:
        if date_str not in _resend_queue:
            _resend_queue.append(date_str)
    logger.info("Queued resend for %s", date_str)

    try:
        from report.email_sender import send_report
        from config.settings import settings
        # If specified date has no report, fall back to latest available
        report_path = settings.data_dir / date_str / "report.html"
        if not report_path.exists():
            data_dir = settings.data_dir
            dates = sorted(
                [d.name for d in data_dir.iterdir()
                 if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"],
                reverse=True,
            )
            for d in dates:
                candidate = settings.data_dir / d / "report.html"
                if candidate.exists():
                    report_path = candidate
                    date_str = d
                    break
        if report_path.exists():
            html = report_path.read_text(encoding="utf-8")
            send_report(date_str, html)
            logger.info("Resend complete for %s", date_str)
        else:
            logger.warning("No report.html found for resend")
    except Exception as exc:
        logger.warning("Resend attempt failed (non-fatal): %s", exc)


# ── Helpers ─────────────────────────────────────────────────────────

def _analyze_news(raw: list[dict], lang: str, dry_run: bool) -> list[dict]:
    if dry_run or not raw:
        return raw
    from analysis.gemini_client import call_gemini_json
    from config.sectors import get_sector_list

    sectors_str = ", ".join(get_sector_list())
    prompt_lines = "\n".join(f'{i+1}. "{item["title"]}"' for i, item in enumerate(raw[:30]))
    prompt = f"""다음 뉴스 제목들을 분석하여 각각에 대해 섹터, 감성, 점수를 JSON 배열로 반환하세요.
섹터는 반드시 다음 중 하나: {sectors_str}
감성: positive, negative, neutral
점수: 1~10 (10이 가장 강한 호재/악재)

뉴스 목록:
{prompt_lines}

JSON 배열 형식:
[{{"index": 1, "sector": "...", "sentiment": "...", "score": 5}}, ...]"""

    result = call_gemini_json(prompt, cache_key=f"news_analysis_{lang}")
    if not result or not isinstance(result, list):
        return raw

    result_map = {item.get("index"): item for item in result if isinstance(item, dict)}
    for i, news in enumerate(raw[:30], 1):
        if i in result_map:
            news["sector"]    = result_map[i].get("sector", "기타")
            news["sentiment"] = result_map[i].get("sentiment", "neutral")
            news["score"]     = int(result_map[i].get("score", 5))
    return raw


def _get_representative_tickers(stocks: list[dict], sectors: list[str]) -> list[tuple]:
    """Return [(sector, ticker, name)] for the top stock in each sector."""
    result = []
    seen_sectors = set()
    for stock in sorted(stocks, key=lambda x: x.get("volume_amount", 0), reverse=True):
        sector = stock.get("sector", "")
        if sector in sectors and sector not in seen_sectors:
            seen_sectors.add(sector)
            result.append((sector, stock["ticker"], stock["name"]))
        if len(seen_sectors) >= len(sectors):
            break
    return result


def _load_backtest(date_str: str) -> list[dict]:
    from storage.github_storage import _get_file_sha
    import requests
    from config.settings import settings
    try:
        resp = requests.get(
            f"https://raw.githubusercontent.com/{settings.github_owner}/{settings.github_repo}/{settings.github_branch}/data/latest.json"
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("backtest_records", [])
    except Exception:
        pass
    return []


def _to_ranking(scores: list[dict]) -> list[dict]:
    return [{"sector": s["sector"], "score": s.get("avg_score", 0), "sentiment": "positive" if s.get("avg_score", 0) >= 6 else ("negative" if s.get("avg_score", 0) < 4 else "neutral")} for s in scores]


def _wrap(date_str: str, data: Any) -> dict:
    return {"ok": True, "date": date_str, "data": data}


def _build_analysis_payload(date_str: str, ctx: dict) -> dict:
    records = []
    for item in ctx.get("korea_news_scores", []):
        sector = item["sector"]
        vol = next((v for v in ctx.get("korea_volume_dist", []) if v["sector"] == sector), {})
        trend = next((t for t in ctx.get("candle_data", []) if t["sector"] == sector), {})
        news_score   = item.get("avg_score", 5)
        volume_score = round(vol.get("ratio", 0) * 100, 1)
        trend_score  = trend.get("momentum_score", 5)
        total        = round((news_score * 0.4 + volume_score * 0.3 + trend_score * 0.3), 2)
        rec_sectors  = ctx.get("ai_recommendation", {}).get("sectors", [])
        records.append({
            "date": date_str,
            "sector": sector,
            "news_score": news_score,
            "volume_score": volume_score,
            "trend_score": trend_score,
            "total_score": total,
            "recommendation": sector in rec_sectors,
            "confidence": ctx.get("ai_recommendation", {}).get("confidence", 0),
        })
    return {"ok": True, "date": date_str, "data": records}


def _build_global_payload(date_str: str, ctx: dict) -> dict:
    g = ctx.get("global_linkage", {})
    return {
        "ok": True, "date": date_str,
        "data": {
            "date": date_str,
            "linkage_cards": g.get("linkage_cards", []),
            "gemini_overall_summary": g.get("gemini_overall_summary", ""),
        }
    }


def _build_report_payload(date_str: str, ctx: dict, drive_url: str) -> dict:
    rec = ctx.get("ai_recommendation", {})
    return {
        "ok": True, "date": date_str,
        "data": {
            "date": date_str,
            "sent_at": datetime.now(KST).isoformat(),
            "send_status": "sent",
            "html_preview_url": drive_url,
            "html_content": ctx.get("report_html", ""),
            "summary_lines": [
                f"주목 섹터: {', '.join(rec.get('sectors', []))}",
                rec.get("reason", "")[:100] if rec.get("reason") else "",
            ],
        }
    }


def _build_backtest_record(date_str: str, ctx: dict) -> dict | None:
    """Compare the most recent prior AI recommendation against today's actual top sectors."""
    import json
    from datetime import datetime as _dt, timedelta

    target_dt = _dt.strptime(date_str, "%Y-%m-%d")

    # Search back up to 7 days for the most recent saved recommendation
    recommended: list[str] = []
    for delta in range(1, 8):
        prior_date = (target_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
        prior_path = settings.data_dir / prior_date / "dashboard.json"
        if not prior_path.exists():
            continue
        try:
            with open(prior_path, encoding="utf-8") as f:
                dash = json.load(f)
            recommended = dash.get("data", {}).get("ai_recommendation", {}).get("sectors", [])
            if recommended:
                break
        except Exception:
            continue

    if not recommended:
        logger.info("Backtest skipped for %s: no prior recommendation found", date_str)
        return None

    # Today's actual top 3 sectors by avg_score (기타 excluded, list already sorted)
    actual_top = [
        s["sector"] for s in ctx.get("korea_news_scores", [])
        if s.get("sector") != "기타"
    ][:3]

    if not actual_top:
        logger.info("Backtest skipped for %s: no actual sector data", date_str)
        return None

    hit  = [s for s in recommended if s in actual_top]
    miss = [s for s in recommended if s not in actual_top]
    accuracy = round(len(hit) / len(recommended), 2) if recommended else 0

    logger.info(
        "Backtest %s: recommended=%s actual=%s accuracy=%.0f%%",
        date_str, recommended, actual_top, accuracy * 100,
    )
    return {
        "date": date_str,
        "recommended_sectors": recommended,
        "actual_top_sectors":  actual_top,
        "accuracy":            accuracy,
        "hit_sectors":         hit,
        "miss_sectors":        miss,
    }


def _build_dashboard_payload(date_str: str, ctx: dict) -> dict:
    rec = ctx.get("ai_recommendation", {})
    return {
        "ok": True, "date": date_str,
        "data": {
            "last_updated": datetime.now(KST).isoformat(),
            "pipeline_status": "success",
            "ai_recommendation": {
                "sectors": rec.get("sectors", []),
                "reason": rec.get("reason", ""),
                "confidence": rec.get("confidence", 0),
                "generated_at": datetime.now(KST).isoformat(),
            },
            "korea_sector_ranking": _to_ranking(ctx.get("korea_news_scores", [])),
            "us_sector_ranking":    _to_ranking(ctx.get("us_news_scores", [])),
            "korea_sector_volume_distribution": ctx.get("korea_volume_dist", []),
            "us_sector_volume_distribution":    ctx.get("us_volume_dist", []),
        }
    }


if __name__ == "__main__":
    import argparse, os, sys
    # Load .env into os.environ BEFORE any library (pykrx reads KRX_ID/KRX_PW directly)
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"),
                    override=False)
    except Exception:
        pass
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        stream=sys.stdout,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",    default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Fall back to environment variables (used by GitHub Actions workflow)
    date_str = args.date or os.environ.get("PIPELINE_DATE") or None
    dry_run  = args.dry_run or os.environ.get("PIPELINE_DRY_RUN", "").lower() == "true"

    ok = run_pipeline(date_str=date_str, dry_run=dry_run)
    sys.exit(0 if ok else 1)
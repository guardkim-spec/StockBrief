"""Integration test: verify pipeline step order and data contract."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config.schedule import PIPELINE_STEPS


def test_pipeline_step_order():
    expected = [
        "korea_price",
        "korea_news",
        "us_price",
        "us_news",
        "gemini_analysis",
        "trend_ai_global",
        "charts_report",
        "storage",
        "email",
    ]
    assert PIPELINE_STEPS == expected


def test_pipeline_step_count():
    assert len(PIPELINE_STEPS) == 9


def test_sector_count():
    from config.sectors import get_sector_list
    sectors = get_sector_list()
    assert len(sectors) == 12


def test_sector_names_no_duplicates():
    from config.sectors import get_sector_list
    sectors = get_sector_list()
    assert len(sectors) == len(set(sectors))


def test_shared_sectors_file_exists():
    from pathlib import Path
    sectors_file = Path(__file__).parent.parent.parent.parent / "shared" / "sectors.json"
    assert sectors_file.exists(), f"shared/sectors.json not found at {sectors_file}"
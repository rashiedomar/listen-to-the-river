#!/usr/bin/env python3
"""Run Sentinel-1 RTC water-mask extraction for the Baladweyne 2023 event.

This wraps the legacy downloader with a local import workaround so the script
can run on this machine.
"""

from __future__ import annotations

from pathlib import Path
import runpy
import sqlite3  # preload before pystac/sqlite-dependent imports
import sys

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SCRIPT = ROOT.parent / "flood-early-warning" / "scripts" / "download_s1_watermasks_stac.py"


def main() -> int:
    if not LEGACY_SCRIPT.exists():
        raise SystemExit(f"Missing legacy dependency: {LEGACY_SCRIPT}")
    sys.argv = [
        "download_s1_watermasks_stac.py",
        "--root",
        str(ROOT),
        "--aoi",
        "study_area/aoi_definition.geojson",
        "--events",
        "config/flood_events.csv",
        "--river",
        "study_area/river_network.geojson",
        "--output-dir",
        "analysis/water_masks_s1_rtc/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD",
        "--event-id",
        "SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD",
        "--lookback-days",
        "21",
        "--tail-days",
        "7",
        "--clear-manifest",
    ]
    runpy.run_path(str(LEGACY_SCRIPT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

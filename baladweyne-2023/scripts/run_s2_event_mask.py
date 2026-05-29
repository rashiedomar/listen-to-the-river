#!/usr/bin/env python3
"""Run Sentinel-2 NDWI flood-mask extraction for the Baladweyne 2023 event."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import sqlite3  # Preload before pystac/sqlite-dependent imports on this machine.

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SCRIPTS = ROOT.parent / "flood-early-warning" / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--event-id",
        default="SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD",
    )
    parser.add_argument(
        "--events-csv",
        default=str(ROOT / "config" / "flood_events.csv"),
    )
    parser.add_argument(
        "--aoi",
        default=str(ROOT / "study_area" / "aoi_definition.geojson"),
    )
    parser.add_argument(
        "--river",
        default=str(ROOT / "study_area" / "river_network.geojson"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "analysis" / "water_masks_s2_ndwi"),
    )
    parser.add_argument("--ndwi-threshold", type=float, default=0.08)
    parser.add_argument("--river-buffer-m", type=float, default=6000.0)
    parser.add_argument("--max-cloud-cover", type=float, default=30.0)
    parser.add_argument("--days-before-peak", type=int, default=30)
    parser.add_argument("--days-after-peak", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    if not LEGACY_SCRIPTS.exists():
        raise SystemExit(f"Missing legacy dependency: {LEGACY_SCRIPTS}")
    sys.path.insert(0, str(LEGACY_SCRIPTS))
    from detect_water_sentinel2_ndwi import process_event

    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = process_event(
        event_id=args.event_id,
        events_csv=args.events_csv,
        aoi_path=args.aoi,
        river_path=args.river,
        output_dir=output_dir,
        ndwi_threshold=args.ndwi_threshold,
        river_buffer_m=args.river_buffer_m,
        max_cloud_cover=args.max_cloud_cover,
        days_before_peak=args.days_before_peak,
        days_after_peak=args.days_after_peak,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

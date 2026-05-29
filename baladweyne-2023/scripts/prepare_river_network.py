#!/usr/bin/env python3
"""Prepare a clean Baladweyne river network layer from raw OSM water features."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_ROOT / "source_data" / "osm" / "waterways.geojson"),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_ROOT / "study_area" / "river_network.geojson"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gdf = gpd.read_file(args.input)

    mask = (
        gdf["feature_type"].astype(str).str.lower().isin(["river", "stream", "canal"])
        | gdf["name"].astype(str).str.contains("Shabelle|Shebelle|Shabeelle|Webi", case=False, na=False)
    )
    river = gdf.loc[mask].copy()
    river["river_name"] = river["name"].fillna("Shabelle (OSM-derived)")
    river["aoi"] = "Baladweyne November 2023 study area"
    river["source"] = "OpenStreetMap via Overpass API"
    river["note"] = "Filtered from OSM water features for flood-mask river QA"
    river = river[["river_name", "aoi", "source", "note", "geometry"]]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    river.to_file(out, driver="GeoJSON")

    print(f"Saved {len(river)} river features to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

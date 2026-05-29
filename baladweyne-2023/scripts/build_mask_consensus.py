#!/usr/bin/env python3
"""Build agreement and disagreement layers between the S2 and S1 flood masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd


CRS = "EPSG:32638"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def area_km2(gdf: gpd.GeoDataFrame) -> float:
    if gdf.empty:
        return 0.0
    return float(gdf.area.sum() / 1_000_000)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    out_dir = root / "analysis" / "mask_consensus"
    out_dir.mkdir(parents=True, exist_ok=True)

    s2 = gpd.read_file(
        root
        / "analysis/water_masks_s2_ndwi/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD/flood_footprint.geojson"
    ).to_crs(CRS)
    s1 = gpd.read_file(
        root
        / "analysis/water_masks_s1_rtc/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD/flood_footprint.geojson"
    ).to_crs(CRS)

    overlap = gpd.overlay(s2[["geometry"]], s1[["geometry"]], how="intersection")
    s2_only = gpd.overlay(s2[["geometry"]], s1[["geometry"]], how="difference")
    s1_only = gpd.overlay(s1[["geometry"]], s2[["geometry"]], how="difference")

    outputs = {
        "overlap": overlap,
        "s2_only": s2_only,
        "s1_only": s1_only,
    }

    for name, gdf in outputs.items():
        if gdf.empty:
            continue
        gdf = gdf.explode(index_parts=False).reset_index(drop=True).to_crs("EPSG:4326")
        gdf.to_file(out_dir / f"{name}.geojson", driver="GeoJSON")

    overlap_area = area_km2(overlap)
    s2_area = area_km2(s2)
    s1_area = area_km2(s1)
    union_area = s2_area + s1_area - overlap_area
    summary = {
        "s2_km2": round(s2_area, 2),
        "s1_km2": round(s1_area, 2),
        "overlap_km2": round(overlap_area, 2),
        "s2_only_km2": round(area_km2(s2_only), 2),
        "s1_only_km2": round(area_km2(s1_only), 2),
        "jaccard": round(overlap_area / union_area, 3) if union_area else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

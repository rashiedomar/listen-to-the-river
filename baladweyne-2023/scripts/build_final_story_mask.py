#!/usr/bin/env python3
"""Build a presentation-ready Baladweyne flood story mask from S2/S1 consensus layers."""

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


def dissolve_to_wgs84(gdf: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    dissolved = gdf[["geometry"]].dissolve()
    dissolved = dissolved.explode(index_parts=False).reset_index(drop=True)
    dissolved["mask_type"] = label
    return dissolved.to_crs("EPSG:4326")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
    )
    parser.add_argument(
        "--min-s1-extension-area-km2",
        type=float,
        default=0.05,
        help="Minimum area for an S1-only extension polygon to be retained.",
    )
    parser.add_argument(
        "--max-s1-overlap-distance-m",
        type=float,
        default=50.0,
        help="Maximum distance from the trusted overlap/core to retain an S1 extension.",
    )
    parser.add_argument(
        "--max-s1-river-distance-m",
        type=float,
        default=2200.0,
        help="Maximum distance from the river corridor to retain an S1 extension.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    out_dir = root / "analysis" / "final_story_mask"
    out_dir.mkdir(parents=True, exist_ok=True)

    s2 = gpd.read_file(
        root
        / "analysis/water_masks_s2_ndwi/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD/flood_footprint.geojson"
    ).to_crs(CRS)
    overlap = gpd.read_file(root / "analysis/mask_consensus/overlap.geojson").to_crs(CRS)
    s1_only = gpd.read_file(root / "analysis/mask_consensus/s1_only.geojson").to_crs(CRS)
    river = gpd.read_file(root / "study_area/river_network.geojson").to_crs(CRS)

    s1_only = s1_only.explode(index_parts=False).reset_index(drop=True)
    overlap_union = overlap.union_all()
    river_union = river.union_all()

    s1_only["area_km2"] = s1_only.area / 1_000_000
    s1_only["dist_overlap_m"] = s1_only.geometry.distance(overlap_union)
    s1_only["dist_river_m"] = s1_only.geometry.distance(river_union)

    selected_s1 = s1_only[
        (s1_only["area_km2"] >= args.min_s1_extension_area_km2)
        & (s1_only["dist_overlap_m"] <= args.max_s1_overlap_distance_m)
        & (s1_only["dist_river_m"] <= args.max_s1_river_distance_m)
    ].copy()

    core_mask = dissolve_to_wgs84(overlap, "core_consensus")
    s1_extension_mask = dissolve_to_wgs84(selected_s1, "s1_extension")

    final_input = gpd.GeoDataFrame(
        geometry=list(s2.geometry) + list(selected_s1.geometry),
        crs=CRS,
    )
    final_story_mask = dissolve_to_wgs84(final_input, "final_story")

    core_mask.to_file(out_dir / "core_flood_mask.geojson", driver="GeoJSON")
    s1_extension_mask.to_file(out_dir / "selected_s1_extensions.geojson", driver="GeoJSON")
    final_story_mask.to_file(out_dir / "final_story_mask.geojson", driver="GeoJSON")

    summary = {
        "parameters": {
            "min_s1_extension_area_km2": args.min_s1_extension_area_km2,
            "max_s1_overlap_distance_m": args.max_s1_overlap_distance_m,
            "max_s1_river_distance_m": args.max_s1_river_distance_m,
        },
        "areas_km2": {
            "s2_base": round(area_km2(s2), 2),
            "core_overlap": round(area_km2(overlap), 2),
            "selected_s1_extensions": round(area_km2(selected_s1), 2),
            "final_story_mask": round(area_km2(final_story_mask.to_crs(CRS)), 2),
        },
        "counts": {
            "selected_s1_extension_polygons": int(len(selected_s1)),
            "core_polygons": int(len(core_mask)),
            "final_story_polygons": int(len(final_story_mask)),
        },
        "outputs": {
            "core_flood_mask": str(out_dir / "core_flood_mask.geojson"),
            "selected_s1_extensions": str(out_dir / "selected_s1_extensions.geojson"),
            "final_story_mask": str(out_dir / "final_story_mask.geojson"),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

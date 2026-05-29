#!/usr/bin/env python3
"""Render a comparison map between Sentinel-2 and Sentinel-1 flood masks."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


CRS = "EPSG:32638"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


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
    out_dir = root / "analysis" / "review_maps"
    out_dir.mkdir(parents=True, exist_ok=True)

    aoi = gpd.read_file(root / "study_area/aoi_definition.geojson").to_crs(CRS)
    city_center = gpd.read_file(root / "study_area/city_center.geojson").to_crs(CRS)
    buildings = gpd.read_file(root / "source_data/osm/buildings.geojson").to_crs(CRS)
    roads = gpd.read_file(root / "source_data/osm/roads.geojson").to_crs(CRS)
    river = gpd.read_file(root / "study_area/river_network.geojson").to_crs(CRS)
    s2 = gpd.read_file(
        root
        / "analysis/water_masks_s2_ndwi/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD/flood_footprint.geojson"
    ).to_crs(CRS)
    s1 = gpd.read_file(
        root
        / "analysis/water_masks_s1_rtc/SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD/flood_footprint.geojson"
    ).to_crs(CRS)

    overlap = gpd.overlay(s2[["geometry"]], s1[["geometry"]], how="intersection")

    fig, axes = plt.subplots(1, 2, figsize=(15, 9), dpi=180)
    fig.patch.set_facecolor("#f8f5ef")
    full_ax, city_ax = axes

    for ax in axes:
        ax.set_facecolor("#fbfaf6")
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    roads.plot(ax=full_ax, color="#c0b9b1", linewidth=0.3, alpha=0.35, zorder=1)
    river.plot(ax=full_ax, color="#284f75", linewidth=0.9, alpha=0.85, zorder=2)
    s2.plot(ax=full_ax, color="#2fb8e9", edgecolor="#0f6f9c", linewidth=0.6, alpha=0.38, zorder=3)
    s1.plot(ax=full_ax, color="#d65aa6", edgecolor="#8c1f5d", linewidth=0.5, alpha=0.24, zorder=4)
    if not overlap.empty:
        overlap.plot(ax=full_ax, color="#5a2f98", edgecolor="#3a1d68", linewidth=0.4, alpha=0.48, zorder=5)
    aoi.boundary.plot(ax=full_ax, color="#4b403e", linewidth=1.0, linestyle="--", alpha=0.85, zorder=6)
    full_ax.set_xlim(aoi.total_bounds[0], aoi.total_bounds[2])
    full_ax.set_ylim(aoi.total_bounds[1], aoi.total_bounds[3])
    full_ax.set_title("Full AOI", fontsize=13, fontweight="bold", color="#250d15", pad=10)

    city_buffer = city_center.to_crs(CRS).buffer(7000)
    city_bbox = city_buffer.total_bounds
    city_buildings = buildings.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]]
    city_roads = roads.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]]
    city_river = river.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]]
    city_s2 = s2.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]]
    city_s1 = s1.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]]
    city_overlap = overlap.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]] if not overlap.empty else overlap

    city_buildings.plot(ax=city_ax, color="#2b201e", linewidth=0, alpha=0.08, zorder=1)
    city_roads.plot(ax=city_ax, color="#c0b9b1", linewidth=0.45, alpha=0.45, zorder=2)
    city_river.plot(ax=city_ax, color="#284f75", linewidth=1.1, alpha=0.9, zorder=3)
    city_s2.plot(ax=city_ax, color="#2fb8e9", edgecolor="#0f6f9c", linewidth=0.65, alpha=0.4, zorder=4)
    city_s1.plot(ax=city_ax, color="#d65aa6", edgecolor="#8c1f5d", linewidth=0.55, alpha=0.25, zorder=5)
    if not city_overlap.empty:
        city_overlap.plot(ax=city_ax, color="#5a2f98", edgecolor="#3a1d68", linewidth=0.45, alpha=0.52, zorder=6)
    city_ax.set_xlim(city_bbox[0], city_bbox[2])
    city_ax.set_ylim(city_bbox[1], city_bbox[3])
    city_ax.set_title("City-core review", fontsize=13, fontweight="bold", color="#250d15", pad=10)

    handles = [
        Patch(facecolor="#2fb8e9", edgecolor="#0f6f9c", alpha=0.38, label="Sentinel-2 mask"),
        Patch(facecolor="#d65aa6", edgecolor="#8c1f5d", alpha=0.28, label="Sentinel-1 mask"),
        Patch(facecolor="#5a2f98", edgecolor="#3a1d68", alpha=0.5, label="Overlap"),
        Line2D([0], [0], color="#284f75", lw=1.0, label="River"),
        Line2D([0], [0], color="#4b403e", lw=1.0, linestyle="--", label="AOI"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.03), fontsize=10)
    fig.suptitle("Baladweyne Flood Mask Comparison", fontsize=22, fontweight="bold", color="#250d15", y=0.98)
    fig.text(0.5, 0.94, "Independent November 2023 masks from Sentinel-2 and Sentinel-1", ha="center", fontsize=11, color="#5f5250")
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])

    out_path = out_dir / "baladweyne_flood_source_comparison.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved source comparison review to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

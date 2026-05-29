#!/usr/bin/env python3
"""Render visual QA overlays for the Baladweyne 2023 flood footprint."""

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
    parser.add_argument(
        "--event-id",
        default="SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD",
    )
    parser.add_argument(
        "--city-buffer-m",
        type=float,
        default=7000.0,
        help="Radius for the city-core review panel",
    )
    return parser.parse_args()


def load_gdf(path: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(path).to_crs(CRS)


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    event_dir = root / "analysis" / "water_masks_s2_ndwi" / args.event_id
    out_dir = root / "analysis" / "review_maps"
    out_dir.mkdir(parents=True, exist_ok=True)

    aoi = load_gdf(root / "study_area" / "aoi_definition.geojson")
    center = load_gdf(root / "study_area" / "city_center.geojson")
    river = load_gdf(root / "study_area" / "river_network.geojson")
    roads = load_gdf(root / "source_data" / "osm" / "roads.geojson")
    buildings = load_gdf(root / "source_data" / "osm" / "buildings.geojson")
    flood = load_gdf(event_dir / "flood_footprint.geojson")

    center_point = center.geometry.iloc[0]
    city_window = center.buffer(args.city_buffer_m)
    city_window_bounds = city_window.total_bounds

    roads_city = gpd.clip(roads, city_window)
    buildings_city = gpd.clip(buildings, city_window)
    river_city = gpd.clip(river, city_window)
    flood_city = gpd.clip(flood, city_window)

    fig, axes = plt.subplots(1, 2, figsize=(18, 10), dpi=180)
    fig.patch.set_facecolor("#f8f5ef")

    for ax in axes:
        ax.set_facecolor("#fbfaf6")
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    # Panel 1: Full AOI review
    ax = axes[0]
    roads.plot(ax=ax, color="#b9b4ac", linewidth=0.35, alpha=0.55, zorder=1)
    river.plot(ax=ax, color="#365d8d", linewidth=0.75, alpha=0.7, zorder=2)
    flood.plot(ax=ax, color="#4aaee8", edgecolor="#186ea8", linewidth=0.7, alpha=0.55, zorder=3)
    aoi.boundary.plot(ax=ax, color="#4b403e", linewidth=1.2, linestyle="--", alpha=0.9, zorder=4)
    ax.scatter([center_point.x], [center_point.y], color="#7f1d1d", s=26, zorder=5)
    ax.text(center_point.x + 900, center_point.y + 900, "Belet Weyne", fontsize=9, color="#2e1b1b", zorder=6)
    ax.set_xlim(aoi.total_bounds[0], aoi.total_bounds[2])
    ax.set_ylim(aoi.total_bounds[1], aoi.total_bounds[3])
    ax.set_title("AOI Review", fontsize=16, color="#2b161c", pad=12, fontweight="bold")

    # Panel 2: City-core review
    ax = axes[1]
    buildings_city.plot(ax=ax, color="#1f1f1f", linewidth=0, alpha=0.16, zorder=1)
    roads_city.plot(ax=ax, color="#6b6761", linewidth=0.55, alpha=0.65, zorder=2)
    river_city.plot(ax=ax, color="#1b4d76", linewidth=1.1, alpha=0.85, zorder=3)
    if not flood_city.empty:
        flood_city.plot(ax=ax, color="#39b9ec", edgecolor="#0d6c9c", linewidth=0.85, alpha=0.58, zorder=4)
    city_window.boundary.plot(ax=ax, color="#8a8277", linewidth=0.9, linestyle=":", alpha=0.85, zorder=5)
    ax.scatter([center_point.x], [center_point.y], color="#7f1d1d", s=22, zorder=6)
    ax.set_xlim(city_window_bounds[0], city_window_bounds[2])
    ax.set_ylim(city_window_bounds[1], city_window_bounds[3])
    ax.set_title("City-Core Review", fontsize=16, color="#2b161c", pad=12, fontweight="bold")

    legend_handles = [
        Patch(facecolor="#39b9ec", edgecolor="#0d6c9c", alpha=0.58, label="Flood mask"),
        Line2D([0], [0], color="#1b4d76", lw=1.1, label="River network"),
        Line2D([0], [0], color="#6b6761", lw=0.8, label="Roads"),
        Patch(facecolor="#1f1f1f", edgecolor="none", alpha=0.16, label="Buildings"),
        Line2D([0], [0], color="#4b403e", lw=1.2, linestyle="--", label="AOI boundary"),
    ]

    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 0.02),
        fontsize=10,
    )
    fig.suptitle(
        "Baladweyne 2023 Flood Mask Review",
        fontsize=22,
        fontweight="bold",
        color="#250d15",
        y=0.98,
    )
    fig.text(
        0.5,
        0.94,
        "Merged Sentinel-2 NDWI flood mask over Baladweyne AOI and city core",
        ha="center",
        fontsize=11,
        color="#5f5250",
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.93])

    out_path = out_dir / "baladweyne_flood_overlay_review.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved review map to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

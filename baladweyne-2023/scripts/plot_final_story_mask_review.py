#!/usr/bin/env python3
"""Render review map for Baladweyne final story mask and high-confidence core."""

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
    final_story = gpd.read_file(root / "analysis/final_story_mask/final_story_mask.geojson").to_crs(CRS)
    core = gpd.read_file(root / "analysis/final_story_mask/core_flood_mask.geojson").to_crs(CRS)
    extensions = gpd.read_file(root / "analysis/final_story_mask/selected_s1_extensions.geojson").to_crs(CRS)

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

    roads.plot(ax=full_ax, color="#c4beb7", linewidth=0.28, alpha=0.35, zorder=1)
    river.plot(ax=full_ax, color="#284f75", linewidth=0.95, alpha=0.9, zorder=2)
    final_story.plot(ax=full_ax, color="#f2a97e", edgecolor="#ab5a2b", linewidth=0.8, alpha=0.34, zorder=3)
    extensions.plot(ax=full_ax, color="#d87db0", edgecolor="#943766", linewidth=0.6, alpha=0.24, zorder=4)
    core.plot(ax=full_ax, color="#55339a", edgecolor="#2f1659", linewidth=0.55, alpha=0.52, zorder=5)
    aoi.boundary.plot(ax=full_ax, color="#4b403e", linewidth=1.0, linestyle="--", alpha=0.85, zorder=6)
    full_ax.set_xlim(aoi.total_bounds[0], aoi.total_bounds[2])
    full_ax.set_ylim(aoi.total_bounds[1], aoi.total_bounds[3])
    full_ax.set_title("Full AOI", fontsize=13, fontweight="bold", color="#250d15", pad=10)

    city_buffer = city_center.buffer(7000)
    city_bbox = city_buffer.total_bounds
    buildings.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#2b201e", linewidth=0, alpha=0.08, zorder=1
    )
    roads.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#c4beb7", linewidth=0.45, alpha=0.45, zorder=2
    )
    river.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#284f75", linewidth=1.1, alpha=0.9, zorder=3
    )
    final_story.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#f2a97e", edgecolor="#ab5a2b", linewidth=0.7, alpha=0.34, zorder=4
    )
    extensions.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#d87db0", edgecolor="#943766", linewidth=0.55, alpha=0.22, zorder=5
    )
    core.cx[city_bbox[0]:city_bbox[2], city_bbox[1]:city_bbox[3]].plot(
        ax=city_ax, color="#55339a", edgecolor="#2f1659", linewidth=0.45, alpha=0.55, zorder=6
    )
    city_ax.set_xlim(city_bbox[0], city_bbox[2])
    city_ax.set_ylim(city_bbox[1], city_bbox[3])
    city_ax.set_title("City-core review", fontsize=13, fontweight="bold", color="#250d15", pad=10)

    handles = [
        Patch(facecolor="#f2a97e", edgecolor="#ab5a2b", alpha=0.34, label="Final story mask"),
        Patch(facecolor="#55339a", edgecolor="#2f1659", alpha=0.52, label="High-confidence core"),
        Patch(facecolor="#d87db0", edgecolor="#943766", alpha=0.24, label="Selected S1 extensions"),
        Line2D([0], [0], color="#284f75", lw=1.0, label="River"),
        Line2D([0], [0], color="#4b403e", lw=1.0, linestyle="--", label="AOI"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.03), fontsize=10)
    fig.suptitle("Baladweyne Final Story Mask Review", fontsize=22, fontweight="bold", color="#250d15", y=0.98)
    fig.text(
        0.5,
        0.94,
        "Presentation-ready flood body = Sentinel-2 event mask plus controlled Sentinel-1 extensions",
        ha="center",
        fontsize=11,
        color="#5f5250",
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])

    out_path = out_dir / "baladweyne_final_story_mask_review.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved final story mask review to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

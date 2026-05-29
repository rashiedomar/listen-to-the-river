#!/usr/bin/env python3
"""Derive Baladweyne flood impact layers from the merged flood footprint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--flood-footprint",
        default=str(
            DEFAULT_ROOT
            / "analysis"
            / "water_masks_s2_ndwi"
            / "SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD"
            / "flood_footprint.geojson"
        ),
    )
    parser.add_argument(
        "--buildings",
        default=str(DEFAULT_ROOT / "source_data" / "osm" / "buildings.geojson"),
    )
    parser.add_argument(
        "--roads",
        default=str(DEFAULT_ROOT / "source_data" / "osm" / "roads.geojson"),
    )
    parser.add_argument(
        "--places",
        default=str(DEFAULT_ROOT / "source_data" / "osm" / "places.geojson"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_ROOT / "analysis" / "impact_layers"),
    )
    parser.add_argument("--proximity-m", type=float, default=50.0)
    return parser.parse_args()


def classify_fraction(frac: float) -> str:
    if frac > 0.5:
        return "severe"
    if frac > 0.1:
        return "moderate"
    if frac > 0:
        return "minor"
    return "none"


def process_buildings(buildings: gpd.GeoDataFrame, flood: gpd.GeoDataFrame, proximity_m: float) -> tuple[gpd.GeoDataFrame, dict]:
    b = buildings.copy()
    b["building_area_m2"] = b.geometry.area
    b["impact_area_m2"] = 0.0
    b["impact_fraction"] = 0.0
    b["impact_level"] = "none"
    b["distance_to_flood_m"] = b.geometry.distance(flood.unary_union)

    intersections = gpd.overlay(
        b[["osm_id", "geometry", "building_area_m2"]],
        flood[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if not intersections.empty:
        intersections["intersect_area_m2"] = intersections.geometry.area
        impacted = intersections.groupby("osm_id", as_index=False)["intersect_area_m2"].sum()
        b = b.merge(impacted, on="osm_id", how="left")
        b["impact_area_m2"] = b["intersect_area_m2"].fillna(0.0)
        b = b.drop(columns=["intersect_area_m2"])
        b["impact_fraction"] = b["impact_area_m2"] / b["building_area_m2"].replace(0, pd.NA)
        b["impact_fraction"] = b["impact_fraction"].fillna(0.0)
        b["impact_level"] = b["impact_fraction"].apply(classify_fraction)

    proximity_mask = (b["impact_level"] == "none") & (b["distance_to_flood_m"] <= proximity_m)
    b.loc[proximity_mask, "impact_level"] = "proximity"

    stats = {
        "total_buildings": int(len(b)),
        "severe": int((b["impact_level"] == "severe").sum()),
        "moderate": int((b["impact_level"] == "moderate").sum()),
        "minor": int((b["impact_level"] == "minor").sum()),
        "proximity": int((b["impact_level"] == "proximity").sum()),
        "total_affected": int(b["impact_level"].isin(["severe", "moderate", "minor", "proximity"]).sum()),
    }
    return b, stats


def process_roads(roads: gpd.GeoDataFrame, flood: gpd.GeoDataFrame, proximity_m: float) -> tuple[gpd.GeoDataFrame, dict]:
    r = roads.copy()
    r["road_length_m"] = r.geometry.length
    r["impact_length_m"] = 0.0
    r["impact_fraction"] = 0.0
    r["impact_level"] = "none"
    r["distance_to_flood_m"] = r.geometry.distance(flood.unary_union)

    intersections = gpd.overlay(
        r[["osm_id", "geometry", "road_length_m"]],
        flood[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if not intersections.empty:
        intersections["intersect_length_m"] = intersections.geometry.length
        impacted = intersections.groupby("osm_id", as_index=False)["intersect_length_m"].sum()
        r = r.merge(impacted, on="osm_id", how="left")
        r["impact_length_m"] = r["intersect_length_m"].fillna(0.0)
        r = r.drop(columns=["intersect_length_m"])
        r["impact_fraction"] = r["impact_length_m"] / r["road_length_m"].replace(0, pd.NA)
        r["impact_fraction"] = r["impact_fraction"].fillna(0.0)
        r["impact_level"] = r["impact_fraction"].apply(classify_fraction)

    proximity_mask = (r["impact_level"] == "none") & (r["distance_to_flood_m"] <= proximity_m)
    r.loc[proximity_mask, "impact_level"] = "proximity"

    stats = {
        "total_roads": int(len(r)),
        "severe": int((r["impact_level"] == "severe").sum()),
        "moderate": int((r["impact_level"] == "moderate").sum()),
        "minor": int((r["impact_level"] == "minor").sum()),
        "proximity": int((r["impact_level"] == "proximity").sum()),
        "total_affected": int(r["impact_level"].isin(["severe", "moderate", "minor", "proximity"]).sum()),
    }
    return r, stats


def process_places(places: gpd.GeoDataFrame, flood: gpd.GeoDataFrame, proximity_m: float) -> tuple[gpd.GeoDataFrame, dict]:
    p = places.copy()
    flood_union = flood.unary_union
    p["distance_to_flood_m"] = p.geometry.distance(flood_union)
    p["impact_level"] = "none"
    p.loc[p.geometry.within(flood_union), "impact_level"] = "severe"
    proximity_mask = (p["impact_level"] == "none") & (p["distance_to_flood_m"] <= proximity_m)
    p.loc[proximity_mask, "impact_level"] = "proximity"

    stats = {
        "total_places": int(len(p)),
        "severe": int((p["impact_level"] == "severe").sum()),
        "proximity": int((p["impact_level"] == "proximity").sum()),
        "total_affected": int(p["impact_level"].isin(["severe", "proximity"]).sum()),
    }
    return p, stats


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    flood = gpd.read_file(args.flood_footprint).to_crs("EPSG:32638")
    buildings = gpd.read_file(args.buildings).to_crs("EPSG:32638")
    roads = gpd.read_file(args.roads).to_crs("EPSG:32638")
    places = gpd.read_file(args.places).to_crs("EPSG:32638")

    buildings_impacted, building_stats = process_buildings(buildings, flood, args.proximity_m)
    roads_impacted, road_stats = process_roads(roads, flood, args.proximity_m)
    places_impacted, place_stats = process_places(places, flood, args.proximity_m)

    buildings_impacted.to_crs("EPSG:4326").to_file(out_dir / "buildings_impacted.geojson", driver="GeoJSON")
    roads_impacted.to_crs("EPSG:4326").to_file(out_dir / "roads_impacted.geojson", driver="GeoJSON")
    places_impacted.to_crs("EPSG:4326").to_file(out_dir / "places_impacted.geojson", driver="GeoJSON")

    buildings_impacted.drop(columns="geometry").to_csv(out_dir / "buildings_impacted.csv", index=False)
    roads_impacted.drop(columns="geometry").to_csv(out_dir / "roads_impacted.csv", index=False)
    places_impacted.drop(columns="geometry").to_csv(out_dir / "places_impacted.csv", index=False)

    summary = {
        "building_stats": building_stats,
        "road_stats": road_stats,
        "place_stats": place_stats,
    }
    (out_dir / "impact_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

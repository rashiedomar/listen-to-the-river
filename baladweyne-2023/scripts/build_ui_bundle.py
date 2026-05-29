#!/usr/bin/env python3
"""Build a lightweight static UI data bundle for the Baladweyne flood story."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd


ROOT = Path(__file__).resolve().parents[1]
UI_DATA = ROOT / "ui" / "data"
PROJECTED_CRS = "EPSG:32638"


def write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")


def keep_columns(gdf: gpd.GeoDataFrame, columns: list[str]) -> gpd.GeoDataFrame:
    keep = [col for col in columns if col in gdf.columns]
    return gdf[keep].copy()


def simplify_for_ui(gdf: gpd.GeoDataFrame, tolerance_m: float) -> gpd.GeoDataFrame:
    projected = gdf.to_crs(PROJECTED_CRS).copy()
    projected["geometry"] = projected.geometry.simplify(tolerance_m, preserve_topology=True)
    return projected.to_crs("EPSG:4326")


def representative_points_for_ui(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    projected = gdf.to_crs(PROJECTED_CRS).copy()
    projected["geometry"] = projected.geometry.representative_point()
    return projected.to_crs("EPSG:4326")


def soften_mask_for_ui(gdf: gpd.GeoDataFrame, expand_m: float, contract_m: float, simplify_m: float) -> gpd.GeoDataFrame:
    projected = gdf.to_crs(PROJECTED_CRS)
    softened = projected.union_all().buffer(expand_m).buffer(-contract_m)
    softened_gdf = gpd.GeoDataFrame(geometry=[softened], crs=PROJECTED_CRS).explode(index_parts=False).reset_index(drop=True)
    softened_gdf["geometry"] = softened_gdf.geometry.simplify(simplify_m, preserve_topology=True)
    return softened_gdf.to_crs("EPSG:4326")


def main() -> int:
    UI_DATA.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((ROOT / "config" / "event_manifest.json").read_text())
    final_summary = json.loads((ROOT / "analysis" / "final_story_mask" / "summary.json").read_text())
    reference_summary = json.loads((ROOT / "analysis" / "mask_consensus" / "summary.json").read_text())
    impact_summary = json.loads((ROOT / "analysis" / "final_story_impacts" / "impact_summary.json").read_text())

    aoi = gpd.read_file(ROOT / "study_area" / "aoi_definition.geojson")
    city_center = gpd.read_file(ROOT / "study_area" / "city_center.geojson")
    river = simplify_for_ui(gpd.read_file(ROOT / "study_area" / "river_network.geojson"), 12)
    final_story = soften_mask_for_ui(
        gpd.read_file(ROOT / "analysis" / "final_story_mask" / "final_story_mask.geojson"),
        expand_m=75,
        contract_m=55,
        simplify_m=22,
    )
    final_story["mask_type"] = "final_story"
    core = soften_mask_for_ui(
        gpd.read_file(ROOT / "analysis" / "final_story_mask" / "core_flood_mask.geojson"),
        expand_m=40,
        contract_m=28,
        simplify_m=16,
    )
    core["mask_type"] = "core"
    extensions = soften_mask_for_ui(
        gpd.read_file(ROOT / "analysis" / "final_story_mask" / "selected_s1_extensions.geojson"),
        expand_m=60,
        contract_m=40,
        simplify_m=24,
    )
    extensions["mask_type"] = "s1_extension"

    roads = gpd.read_file(ROOT / "analysis" / "final_story_impacts" / "roads_impacted.geojson")
    roads = roads.loc[roads["impact_level"] != "none"].copy()
    roads = keep_columns(
        roads,
        ["osm_id", "name", "feature_type", "impact_level", "impact_fraction", "distance_to_flood_m", "geometry"],
    )
    roads = simplify_for_ui(roads, 8)

    places = gpd.read_file(ROOT / "analysis" / "final_story_impacts" / "places_impacted.geojson")
    places = places.loc[places["impact_level"] != "none"].copy()
    places = keep_columns(places, ["name", "place", "impact_level", "distance_to_flood_m", "geometry"])

    buildings = gpd.read_file(ROOT / "analysis" / "final_story_impacts" / "buildings_impacted.geojson")
    buildings = buildings.loc[buildings["impact_level"] != "none"].copy()
    buildings = keep_columns(
        buildings,
        ["osm_id", "impact_level", "impact_fraction", "distance_to_flood_m", "geometry"],
    )
    buildings["impact_fraction"] = buildings["impact_fraction"].round(3)
    buildings["distance_to_flood_m"] = buildings["distance_to_flood_m"].round(1)
    buildings = representative_points_for_ui(buildings)

    write_geojson(aoi[["geometry"]], UI_DATA / "aoi.geojson")
    write_geojson(city_center[["geometry"]], UI_DATA / "city_center.geojson")
    write_geojson(river[["river_name", "geometry"]], UI_DATA / "river.geojson")
    write_geojson(final_story[["mask_type", "geometry"]], UI_DATA / "final_story_mask.geojson")
    write_geojson(core[["mask_type", "geometry"]], UI_DATA / "core_mask.geojson")
    write_geojson(extensions[["mask_type", "geometry"]], UI_DATA / "s1_extensions.geojson")
    write_geojson(roads, UI_DATA / "roads_impacted.geojson")
    write_geojson(places, UI_DATA / "places_impacted.geojson")
    write_geojson(buildings, UI_DATA / "buildings_impacted.geojson")

    story_meta = {
        "title": "Listen to the River",
        "subtitle": "Baladweyne, November 2023",
        "event_id": manifest["event_id"],
        "label": manifest["focus_event"]["label"],
        "city": manifest["city"],
        "country": manifest["country"],
        "river": manifest["river"],
        "focus_dates": manifest["focus_event"],
        "reference_documents": manifest["source_documents"][:2],
        "areas_km2": final_summary["areas_km2"],
        "consensus_summary": reference_summary,
        "impact_summary": impact_summary,
        "layer_labels": {
            "roads": "Roads",
            "buildings": "Buildings",
            "places": "Places",
            "core": "Confidence core",
            "extensions": "S1 fringe",
        },
    }
    (UI_DATA / "story_meta.json").write_text(json.dumps(story_meta, indent=2))
    print(json.dumps({"ui_data_dir": str(UI_DATA), "story_meta": str(UI_DATA / "story_meta.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

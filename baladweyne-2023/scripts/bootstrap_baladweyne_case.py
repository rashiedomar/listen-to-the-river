#!/usr/bin/env python3
"""Bootstrap the Baladweyne 2023 case-study asset pack.

This script creates the first geography and source files needed to rebuild the
project around the November 2023 Baladweyne flood event:

1. Geocode the city center and city bounding box from OSM Nominatim.
2. Build a buffered AOI polygon around the city.
3. Pull base OSM layers via Overpass:
   - buildings
   - roads
   - waterways / water bodies
   - named places
4. Write a summary JSON and event manifest for the new case study.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, Point, Polygon, box


USER_AGENT = "codex-baladweyne-bootstrap/1.0"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = DEFAULT_ROOT.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Case-study root directory",
    )
    parser.add_argument(
        "--query",
        default="Beledweyne, Somalia",
        help="Primary geocoding query used against Nominatim",
    )
    parser.add_argument(
        "--aliases",
        nargs="*",
        default=["Baladweyne", "Belet Weyne", "Beledweyne"],
        help="Common city aliases stored in the event manifest",
    )
    parser.add_argument(
        "--buffer-km",
        type=float,
        default=10.0,
        help="Buffer added around the city bbox to build the study AOI",
    )
    parser.add_argument(
        "--bulletins-csv",
        default=str(
            WORKSPACE_ROOT / "flood-early-warning" / "03_data" / "hydromet" / "raw" / "faoswalim_bulletins_2026-02-03.csv"
        ),
        help="Optional SWALIM bulletin archive CSV used to seed sources",
    )
    return parser.parse_args()


def geocode_city(query: str) -> dict:
    response = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 5},
        headers={"User-Agent": USER_AGENT},
        timeout=90,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise RuntimeError(f"No Nominatim result for query: {query}")
    return results[0]


def build_aoi(place: dict, buffer_km: float) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    south, north, west, east = map(float, place["boundingbox"])
    city_bbox = box(west, south, east, north)
    city_center = Point(float(place["lon"]), float(place["lat"]))

    city_gdf = gpd.GeoDataFrame(
        [
            {
                "name": place["display_name"],
                "query_name": place["name"],
                "osm_type": place["osm_type"],
                "osm_id": int(place["osm_id"]),
                "lat": float(place["lat"]),
                "lon": float(place["lon"]),
            }
        ],
        geometry=[city_center],
        crs="EPSG:4326",
    )

    bbox_gdf = gpd.GeoDataFrame(
        [
            {
                "aoi_name": "Baladweyne November 2023 flood study area",
                "city_query": place["name"],
                "buffer_km": buffer_km,
                "source": "OpenStreetMap Nominatim city bounding box with metric buffer",
            }
        ],
        geometry=[city_bbox],
        crs="EPSG:4326",
    )
    bbox_utm = bbox_gdf.to_crs("EPSG:32638")
    aoi_utm = bbox_utm.buffer(buffer_km * 1000.0)
    aoi_gdf = gpd.GeoDataFrame(bbox_gdf.drop(columns="geometry"), geometry=aoi_utm, crs="EPSG:32638").to_crs(
        "EPSG:4326"
    )
    return city_gdf, aoi_gdf


def overpass_query(query: str) -> dict:
    response = requests.post(
        OVERPASS_URL,
        data=query.encode("utf-8"),
        headers={"User-Agent": USER_AGENT},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def way_elements_to_gdf(elements: Iterable[dict], geometry_kind: str) -> gpd.GeoDataFrame:
    rows: list[dict] = []
    geoms = []
    for element in elements:
        coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
        if len(coords) < 2:
            continue
        tags = element.get("tags", {})

        geom = None
        if geometry_kind == "polygon":
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            if len(coords) >= 4:
                geom = Polygon(coords)
        elif geometry_kind == "line":
            geom = LineString(coords)

        if geom is None or geom.is_empty:
            continue

        rows.append(
            {
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "name": tags.get("name"),
                "feature_type": tags.get("building")
                or tags.get("highway")
                or tags.get("waterway")
                or tags.get("natural")
                or tags.get("water"),
                "tags_json": json.dumps(tags, sort_keys=True),
            }
        )
        geoms.append(geom)

    return gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")


def node_elements_to_gdf(elements: Iterable[dict]) -> gpd.GeoDataFrame:
    rows: list[dict] = []
    geoms = []
    for element in elements:
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            continue
        tags = element.get("tags", {})
        rows.append(
            {
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "name": tags.get("name"),
                "place": tags.get("place"),
                "tags_json": json.dumps(tags, sort_keys=True),
            }
        )
        geoms.append(Point(float(lon), float(lat)))
    return gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")


def fetch_osm_layers(aoi: gpd.GeoDataFrame) -> dict[str, gpd.GeoDataFrame]:
    west, south, east, north = aoi.total_bounds
    bbox = f"{south},{west},{north},{east}"

    building_query = f"""
[out:json][timeout:180];
(
  way["building"]({bbox});
);
out body geom;
"""
    road_query = f"""
[out:json][timeout:180];
(
  way["highway"]["highway"!~"footway|path|cycleway|steps|service|track"]({bbox});
);
out body geom;
"""
    water_query = f"""
[out:json][timeout:180];
(
  way["waterway"]({bbox});
  way["natural"="water"]({bbox});
  way["water"]({bbox});
);
out body geom;
"""
    place_query = f"""
[out:json][timeout:180];
(
  node["place"]["name"]({bbox});
);
out body;
"""

    building_gdf = way_elements_to_gdf(overpass_query(building_query).get("elements", []), "polygon")
    roads_gdf = way_elements_to_gdf(overpass_query(road_query).get("elements", []), "line")
    waterways_gdf = way_elements_to_gdf(overpass_query(water_query).get("elements", []), "line")
    places_gdf = node_elements_to_gdf(overpass_query(place_query).get("elements", []))

    if not building_gdf.empty:
        building_gdf = gpd.clip(building_gdf, aoi)
    if not roads_gdf.empty:
        roads_gdf = gpd.clip(roads_gdf, aoi)
    if not waterways_gdf.empty:
        waterways_gdf = gpd.clip(waterways_gdf, aoi)
    if not places_gdf.empty:
        places_gdf = gpd.clip(places_gdf, aoi)

    return {
        "buildings": building_gdf,
        "roads": roads_gdf,
        "waterways": waterways_gdf,
        "places": places_gdf,
    }


def extract_bulletin_sources(path: Path) -> list[dict]:
    fallback = [
        {
            "title": "BeletWeyne Flood Advisory - Issued 08 May 2023",
            "url": "https://faoswalim.org/content/beletweyne-flood-advisory-issued-08-may-2023",
            "kind": "advisory",
        },
        {
            "title": "Beletweyne Riverine Flood Impact Map - Issued 17 November 2023",
            "url": "https://faoswalim.org/content/beletweyne-riverine-flood-impact-map-issued-17-november-2023",
            "kind": "impact_map",
        },
        {
            "title": "Beletweyne Riverine Flood Impact Map - Issued 21 November 2023",
            "url": "https://faoswalim.org/content/beletweyne-riverine-flood-impact-map-issued-21-november-2023",
            "kind": "impact_map",
        },
    ]
    if not path.exists():
        return fallback

    df = pd.read_csv(path)
    if "title" not in df.columns or "url" not in df.columns:
        return fallback

    mask = df["title"].str.contains("Beletweyne|Belet Weyne|Baladweyne|Beledweyne", case=False, na=False)
    selected = df.loc[mask, [c for c in ["title", "url", "pub_date"] if c in df.columns]].copy()
    if selected.empty:
        return fallback

    out = []
    for row in selected.head(10).itertuples(index=False):
        title = getattr(row, "title")
        url = getattr(row, "url")
        pub_date = getattr(row, "pub_date", None)
        kind = "impact_map" if "impact map" in title.lower() else "bulletin"
        out.append({"title": title, "url": url, "pub_date": pub_date, "kind": kind})
    return out


def write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)

    city_gdf, aoi_gdf = build_aoi(geocode_city(args.query), args.buffer_km)
    write_geojson(city_gdf, root / "study_area/city_center.geojson")
    write_geojson(aoi_gdf, root / "study_area/aoi_definition.geojson")

    layers = fetch_osm_layers(aoi_gdf)
    for name, gdf in layers.items():
        write_geojson(gdf, root / f"source_data/osm/{name}.geojson")

    sources = extract_bulletin_sources(Path(args.bulletins_csv))
    event_manifest = {
        "event_id": "SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD",
        "city": "Baladweyne",
        "city_aliases": args.aliases,
        "country": "Somalia",
        "river": "Shabelle",
        "focus_event": {
            "start_date": "2023-11-17",
            "peak_date": "2023-11-21",
            "end_date": "2023-11-21",
            "label": "Baladweyne November 2023 riverine flood",
        },
        "recommended_analysis_window": {
            "start_date": "2023-09-01",
            "end_date": "2023-12-15",
        },
        "hydrology": {
            "snrfa_station": "SH001",
            "frrims_station_id": 4,
            "station_name": "Belet Weyne",
        },
        "geocoded_place": city_gdf.drop(columns="geometry").iloc[0].to_dict(),
        "aoi_bounds_wgs84": [float(v) for v in aoi_gdf.total_bounds],
        "source_documents": sources,
    }
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config/event_manifest.json").write_text(json.dumps(event_manifest, indent=2))

    summary = {
        "city_query": args.query,
        "buffer_km": args.buffer_km,
        "aoi_bounds_wgs84": [float(v) for v in aoi_gdf.total_bounds],
        "feature_counts": {name: int(len(gdf)) for name, gdf in layers.items()},
        "outputs": {
            "city_center": "study_area/city_center.geojson",
            "aoi_definition": "study_area/aoi_definition.geojson",
            "event_manifest": "config/event_manifest.json",
            **{name: f"source_data/osm/{name}.geojson" for name in layers},
        },
    }
    (root / "config/bootstrap_summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

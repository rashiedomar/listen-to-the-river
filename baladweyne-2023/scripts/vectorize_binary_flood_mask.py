#!/usr/bin/env python3
"""Convert a binary flood mask raster into a dissolved GeoJSON footprint."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio import features
from rasterio.features import sieve
from shapely.geometry import shape


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mask", required=True, help="Path to binary flood mask TIFF")
    parser.add_argument("--output", required=True, help="Output GeoJSON path")
    parser.add_argument(
        "--sieve-size",
        type=int,
        default=0,
        help="Minimum connected pixel count to retain before polygonization",
    )
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=6.0,
        help="Geometry simplify tolerance in meters after reprojection to WGS84",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mask_path = Path(args.mask)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(mask_path) as src:
        arr = src.read(1)
        transform = src.transform
        crs = src.crs
        water_mask = arr == 1

        if args.sieve_size > 0:
            cleaned = sieve(water_mask.astype("uint8"), size=args.sieve_size)
            water_mask = cleaned == 1

        polygons = [shape(geom) for geom, value in features.shapes(arr, mask=water_mask, transform=transform) if value == 1]

    if not polygons:
        raise SystemExit(f"No flood polygons found in {mask_path}")

    gdf = gpd.GeoDataFrame({"source": ["sentinel1_change"] * len(polygons)}, geometry=polygons, crs=crs)
    gdf = gdf.dissolve()
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    gdf = gdf.to_crs("EPSG:4326")

    if args.simplify_tolerance > 0:
        tolerance_deg = args.simplify_tolerance / 111000.0
        gdf["geometry"] = gdf.geometry.simplify(tolerance_deg, preserve_topology=True)

    gdf.to_file(output_path, driver="GeoJSON")
    print(f"Saved {len(gdf)} polygon(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

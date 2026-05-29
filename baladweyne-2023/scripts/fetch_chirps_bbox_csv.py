#!/usr/bin/env python3
"""Fetch CHIRPS daily rainfall over a bounding box using ERDDAP CSV output.

This avoids NetCDF backend issues and writes one daily mean timeseries for the
AOI bbox.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd


BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lon-min", type=float, required=True)
    parser.add_argument("--lon-max", type=float, required=True)
    parser.add_argument("--lat-min", type=float, required=True)
    parser.add_argument("--lat-max", type=float, required=True)
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def nearest_value(values: pd.Series, target: float) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna().reset_index(drop=True)
    return float(numeric.iloc[int((numeric - target).abs().idxmin())])


def main() -> int:
    args = parse_args()

    lat_df = pd.read_csv(f"{BASE}.csv?latitude", comment="#")
    lon_df = pd.read_csv(f"{BASE}.csv?longitude", comment="#")
    time_df = pd.read_csv(f"{BASE}.csv?time", comment="#")

    lats = lat_df["latitude"]
    lons = lon_df["longitude"]
    times = pd.to_datetime(time_df["time"], errors="coerce", utc=True).dropna().dt.tz_convert(None)

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end) if args.end else times.max()

    lat_start = nearest_value(lats, min(args.lat_min, args.lat_max))
    lat_end = nearest_value(lats, max(args.lat_min, args.lat_max))
    lon_start = nearest_value(lons, min(args.lon_min, args.lon_max))
    lon_end = nearest_value(lons, max(args.lon_min, args.lon_max))
    time_start = times.iloc[int((times - start).abs().argmin())]
    time_end = times.iloc[int((times - end).abs().argmin())]

    raw_frames = []
    cursor = start.normalize()
    while cursor <= end.normalize():
        year_end = pd.Timestamp(dt.date(cursor.year, 12, 31))
        chunk_end = min(end.normalize(), year_end)
        query = (
            f"precip[({cursor.strftime('%Y-%m-%dT00:00:00Z')}):1:({chunk_end.strftime('%Y-%m-%dT00:00:00Z')})]"
            f"[({lat_start}):1:({lat_end})]"
            f"[({lon_start}):1:({lon_end})]"
        )
        url = f"{BASE}.csv?{query}"
        chunk = pd.read_csv(url, comment="#", low_memory=False)
        raw_frames.append(chunk)
        cursor = pd.Timestamp(dt.date(cursor.year + 1, 1, 1))

    raw = pd.concat(raw_frames, ignore_index=True)
    raw["time"] = pd.to_datetime(raw["time"], errors="coerce", utc=True).dt.tz_convert(None)
    raw["precip"] = pd.to_numeric(raw["precip"], errors="coerce")

    out = (
        raw.groupby(raw["time"].dt.date, dropna=True)["precip"]
        .mean()
        .reset_index()
        .rename(columns={"time": "date", "precip": "mean_rain_mm"})
    )
    out["date"] = pd.to_datetime(out["date"])
    out["sum_7d"] = out["mean_rain_mm"].rolling(7, min_periods=1).sum()
    out["sum_30d"] = out["mean_rain_mm"].rolling(30, min_periods=1).sum()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    print(f"Saved {len(out)} rows to {out_path}")
    print(f"Date range: {out['date'].min().date()} to {out['date'].max().date()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

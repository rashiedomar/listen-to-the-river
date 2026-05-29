#!/usr/bin/env python3
"""Build flood-change masks from pre/post Sentinel-1 binary water masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENT_DIR = DEFAULT_ROOT / "analysis" / "water_masks_s1_rtc" / "SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pre-mask",
        default=str(
            DEFAULT_EVENT_DIR
            / "watermask_SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD_20231102_S1A_IW_GRDH_1SDV_20231102T024613_20231102T024638_051032_062745_rtc.tif"
        ),
    )
    parser.add_argument(
        "--post-mask",
        default=str(
            DEFAULT_EVENT_DIR
            / "watermask_SOM_NOV2023_BALADWEYNE_RIVERINE_FLOOD_20231126_S1A_IW_GRDH_1SDV_20231126T024612_20231126T024637_051382_063355_rtc.tif"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_EVENT_DIR),
    )
    return parser.parse_args()


def write_mask(path: Path, arr: np.ndarray, profile: dict) -> None:
    profile = profile.copy()
    profile.update(dtype="uint8", count=1, nodata=255, compress="LZW")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("uint8"), 1)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(args.pre_mask) as pre_src, rasterio.open(args.post_mask) as post_src:
        pre = pre_src.read(1)
        post = post_src.read(1)
        profile = post_src.profile

    valid = (pre != 255) & (post != 255)
    pre_water = (pre == 1) & valid
    post_water = (post == 1) & valid

    flood_only = np.full(pre.shape, 255, dtype=np.uint8)
    stable_water = np.full(pre.shape, 255, dtype=np.uint8)
    receded_water = np.full(pre.shape, 255, dtype=np.uint8)

    flood_only_values = ((post_water) & (~pre_water)).astype("uint8")
    stable_water_values = ((post_water) & (pre_water)).astype("uint8")
    receded_water_values = ((pre_water) & (~post_water)).astype("uint8")

    flood_only[valid] = flood_only_values[valid]
    stable_water[valid] = stable_water_values[valid]
    receded_water[valid] = receded_water_values[valid]

    flood_only_path = out_dir / "s1_flood_only_20231126_vs_20231102.tif"
    stable_path = out_dir / "s1_stable_water_20231126_vs_20231102.tif"
    receded_path = out_dir / "s1_receded_water_20231126_vs_20231102.tif"
    write_mask(flood_only_path, flood_only, profile)
    write_mask(stable_path, stable_water, profile)
    write_mask(receded_path, receded_water, profile)

    summary = {
        "valid_pixels": int(valid.sum()),
        "pre_water_pixels": int(pre_water.sum()),
        "post_water_pixels": int(post_water.sum()),
        "flood_only_pixels": int(((post_water) & (~pre_water)).sum()),
        "stable_water_pixels": int(((post_water) & (pre_water)).sum()),
        "receded_water_pixels": int(((pre_water) & (~post_water)).sum()),
        "outputs": {
            "flood_only": f"analysis/water_masks_s1_rtc/{out_dir.name}/{flood_only_path.name}",
            "stable_water": f"analysis/water_masks_s1_rtc/{out_dir.name}/{stable_path.name}",
            "receded_water": f"analysis/water_masks_s1_rtc/{out_dir.name}/{receded_path.name}",
        },
    }
    (out_dir / "s1_change_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

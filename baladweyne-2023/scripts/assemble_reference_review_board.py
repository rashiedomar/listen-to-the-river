#!/usr/bin/env python3
"""Assemble a single review board from official SWALIM reference maps and local mask comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BG = "#f5f0e8"
INK = "#2a1018"
SUB = "#6b5d5c"
PANEL = "#fbf8f3"
LINE = "#d9cec5"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_image(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    ratio = min(box_w / img.width, box_h / img.height)
    size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(size, Image.Resampling.LANCZOS)


def draw_panel(canvas: Image.Image, x: int, y: int, w: int, h: int, title: str, subtitle: str, img: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=PANEL, outline=LINE, width=2)
    title_font = load_font(26, bold=True)
    subtitle_font = load_font(16)
    draw.text((x + 26, y + 18), title, fill=INK, font=title_font)
    draw.text((x + 26, y + 56), subtitle, fill=SUB, font=subtitle_font)

    inner_x = x + 20
    inner_y = y + 92
    inner_w = w - 40
    inner_h = h - 112
    fitted = fit_image(img, inner_w, inner_h)
    paste_x = inner_x + (inner_w - fitted.width) // 2
    paste_y = inner_y + (inner_h - fitted.height) // 2
    canvas.paste(fitted, (paste_x, paste_y))


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
    reference_dir = root / "analysis" / "reference_review"
    review_dir = root / "analysis" / "review_maps"

    img_17 = Image.open(reference_dir / "baladweyne_reference_20231117.png").convert("RGB")
    img_21 = Image.open(reference_dir / "baladweyne_reference_20231121.png").convert("RGB")
    img_cmp = Image.open(review_dir / "baladweyne_flood_source_comparison.png").convert("RGB")

    width = 2500
    height = 1600
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)

    title_font = load_font(58, bold=True)
    sub_font = load_font(24)
    note_font = load_font(18)

    draw.text((90, 56), "Baladweyne Flood Reference Review", fill=INK, font=title_font)
    draw.text(
        (90, 128),
        "Official SWALIM event maps against our independent Sentinel-2 and Sentinel-1 flood masks.",
        fill=SUB,
        font=sub_font,
    )

    panel_y = 210
    panel_h = 1220
    gap = 36
    panel_w = (width - 180 - (2 * gap)) // 3

    draw_panel(
        canvas,
        90,
        panel_y,
        panel_w,
        panel_h,
        "Official map · 17 Nov 2023",
        "SWALIM district impact map. Reported flooded area: 20,620 ha.",
        img_17,
    )
    draw_panel(
        canvas,
        90 + panel_w + gap,
        panel_y,
        panel_w,
        panel_h,
        "Official map · 21 Nov 2023",
        "SWALIM district impact map. Reported flooded area: 41,384 ha.",
        img_21,
    )
    draw_panel(
        canvas,
        90 + 2 * (panel_w + gap),
        panel_y,
        panel_w,
        panel_h,
        "Our masks · S2 / S1 / overlap",
        "S2: 103.68 km² · S1: 180.77 km² · overlap: 72.60 km² · Jaccard 0.343",
        img_cmp,
    )

    note = (
        "Reading: the official 21 Nov footprint supports a broader flood envelope than the Sentinel-2 mask alone. "
        "The overlap layer remains the safest high-confidence core, while the Sentinel-1-only zone is useful as a wider "
        "context band rather than automatic truth."
    )
    draw.multiline_text((90, 1460), note, fill=SUB, font=note_font, spacing=6)

    out_path = review_dir / "baladweyne_reference_judgement_board.png"
    canvas.save(out_path, quality=95)
    print(f"Saved review board to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

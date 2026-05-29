# Baladweyne 2023 Flood Dashboard

<p>
  <a href="https://rashiedomar.github.io/listen-to-the-river/">
    <img alt="See the live page here" src="https://img.shields.io/badge/See%20the%20live%20page%20here-0F766E?style=for-the-badge">
  </a>
</p>

This case study packages the November 2023 Baladweyne flood as a publishable event dashboard built from satellite analysis, impact overlays, and a cleaned static web interface.

## Project scope

- city: `Baladweyne`
- aliases: `Belet Weyne`, `Beledweyne`
- country: `Somalia`
- river: `Shabelle`
- focus event window: `2023-11-17` to `2023-11-21`

## What is in this case study

The published Baladweyne workflow combines:

- `Sentinel-2` optical flood delineation
- `Sentinel-1` pre/post-event SAR change detection
- a fused final story mask built from a high-confidence overlap core plus selected SAR-only extensions
- impact layers for buildings, roads, and named places
- a static dashboard under `ui/` that reads a prebuilt lightweight GeoJSON bundle

## Key tracked results

From the current event summaries:

- S2 base flood area: `103.68 km²`
- S1 flood-only area: `180.77 km²`
- S1/S2 overlap core: `72.60 km²`
- final story mask: `196.03 km²`
- total affected buildings: `6,460`
- total affected roads: `542`
- total affected named places: `19`

These figures come from:

- `analysis/final_story_mask/summary.json`
- `analysis/mask_consensus/summary.json`
- `analysis/final_story_impacts/impact_summary.json`

## Dashboard data bundle

The deployed UI reads these files from `ui/data/`:

- `story_meta.json`
- `city_center.geojson`
- `final_story_mask.geojson`
- `core_mask.geojson`
- `s1_extensions.geojson`
- `roads_impacted.geojson`
- `buildings_impacted.geojson`
- `places_impacted.geojson`
- `river.geojson`

This bundle is intentionally simplified for web delivery.

## Main folders

- `config/`
  - event metadata and bootstrap outputs
- `study_area/`
  - AOI and river geometry
- `source_data/`
  - retained lightweight source tables and reference inputs
- `analysis/`
  - tracked event summaries
- `scripts/`
  - case-study processing and UI-bundle build helpers
- `ui/`
  - static site for GitHub Pages

## Local run

Serve the dashboard locally:

```bash
cd ui
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Rebuild the UI bundle

If analysis outputs or metadata change, rebuild the lightweight web bundle with:

```bash
python scripts/build_ui_bundle.py
```

## Notes

- The public repo keeps the dashboard-ready bundle and key summaries.
- Heavier rasters, review boards, and bulky local-only intermediates stay outside the published surface.
- The Pages deployment workflow publishes this dashboard at the repo site root.

# Listen to the River

<p>
  <a href="https://rashiedomar.github.io/listen-to-the-river/">
    <img alt="See the live page here" src="https://img.shields.io/badge/See%20the%20live%20page%20here-0F766E?style=for-the-badge">
  </a>
</p>

`Listen to the River` is a satellite-based flood analysis project focused on Somali river systems, with a published Baladweyne 2023 case study that combines optical water mapping, SAR change analysis, and impact-layer storytelling in one web dashboard.

## Published focus

This first public repo pass is centered on:

- the Baladweyne, Somalia flood event of November 2023
- a cleaned static web dashboard under `baladweyne-2023/ui/`
- the supporting scripts, summaries, and lightweight geodata needed to explain and reproduce the published case study surface

The broader early-warning research workspace exists, but the heavier local-only processing branches and raw rasters are intentionally excluded from the public repo surface.

## What this project does

The Baladweyne case study was built to answer a practical question:

`What flood story can be defended when optical, radar, and impact layers are combined into one interpretable event map?`

The published workflow uses:

- `Sentinel-2` water detection to establish the main event footprint
- `Sentinel-1` pre/post-event change analysis to recover additional flood fringe context
- agreement filtering between the two sources to isolate a stricter confidence core
- impact overlays against roads, buildings, and named places to translate water extent into human relevance

## Baladweyne 2023 summary

Current tracked summary from the published event pack:

- final story mask: `196.03 km²`
- strict S1/S2 overlap core: `72.60 km²`
- selected SAR-only extensions: `92.35 km²`
- total affected buildings: `6,460`
- total affected roads: `542`
- total affected named places: `19`

These numbers are stored in:

- `baladweyne-2023/analysis/final_story_mask/summary.json`
- `baladweyne-2023/analysis/final_story_impacts/impact_summary.json`
- `baladweyne-2023/analysis/mask_consensus/summary.json`

## Repository layout

- `baladweyne-2023/`
  - published event case study
- `baladweyne-2023/ui/`
  - static dashboard deployed to GitHub Pages
- `baladweyne-2023/ui/data/`
  - lightweight GeoJSON/JSON bundle used directly by the dashboard
- `baladweyne-2023/scripts/`
  - event-pack and UI-bundle build scripts
- `baladweyne-2023/study_area/`
  - AOI and river context
- `baladweyne-2023/source_data/`
  - selected lightweight reference inputs retained in the repo

## Methods

This repo reflects a mixed analysis workflow rather than a single model:

- optical flood delineation
- SAR-based flood change extraction
- rule-based mask fusion
- GIS impact analysis
- static web presentation

The aim is not just detection. The aim is to produce a flood narrative surface that can be reviewed, explained, and reused.

## Local run

The deployed site is a static bundle. To open it locally:

```bash
cd baladweyne-2023/ui
python -m http.server 8000
```

Then open `http://localhost:8000`.

If the UI data bundle needs to be rebuilt:

```bash
cd baladweyne-2023
python scripts/build_ui_bundle.py
```

## Deployment

GitHub Pages is deployed from `.github/workflows/deploy-pages.yml` and publishes:

- `baladweyne-2023/ui/`

The expected live URL is:

- `https://rashiedomar.github.io/listen-to-the-river/`

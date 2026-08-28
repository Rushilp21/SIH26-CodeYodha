# Shared schemas (team contract)

This folder is the **only** shared ownership area besides documentation.

If you change a schema:

1. Tell the whole team (Dev 1–6).
2. Note the change in `CONTRIBUTING.md` / PR description.
3. Do not silently break API or GeoJSON contracts.

## CRS

- Storage / API / frontend geometry: `STORAGE_CRS` (default `EPSG:4326`).
- Metric processing: `PROCESSING_CRS` (default `EPSG:32645` for Ranchi / UTM 45N).
- Never mix lon/lat with metre calculations.

## Handoffs

| From | To | Contract |
|------|-----|----------|
| Dev 1 | Dev 2 | `geojson/segmentation-output.schema.json` |
| Dev 2 | Backend (Dev 4) | `geojson/refined-parcel.schema.json` |
| API | Frontends | `api/*.schema.json` |

## Confidence bands (frozen)

- HIGH: `confidence >= 0.85` → auto-approval eligible
- MEDIUM: `0.60 <= confidence < 0.85` → review
- LOW: `confidence < 0.60` → field verification

See `api/confidence-bands.schema.json`.

ML modules communicate through these files, **not** by importing another developer's Python package.

# Image ingestion + preprocessing (Developer 1 ONLY)

## Purpose
Ingest drone RGB / ORI / DSM-DTM, preprocess, tile, georeference.

## Owner
Developer 1.

## Inputs
Rasters + metadata. `STORAGE_CRS` / `PROCESSING_CRS` from env.

## Outputs
Tiles + georeferenced rasters for segmentation. Do not call Dev 2 code.

## Dependencies
rasterio, opencv (later). Convert to `PROCESSING_CRS` before metric ops.

## Tests
`pytest ml-pipeline/ingestion/tests`

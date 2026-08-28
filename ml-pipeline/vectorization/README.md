# Vectorization + topology (Developer 2 ONLY)

## Purpose
Raster-to-polygon, topology validation. Handoff into RL refinement.

## Owner
Developer 2.

## Inputs
Dev 1 GeoJSON (`segmentation-output.schema.json`). Raster masks if needed.

## Outputs
Valid polygons. Topology flags. Must reproject to `PROCESSING_CRS` for metric checks, then store as `STORAGE_CRS`.

## Tests
`pytest ml-pipeline/vectorization/tests`

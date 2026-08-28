# Segmentation (Developer 1 ONLY)

## Purpose
Parcel / building / road / land-use extraction. Export GeoJSON to Dev 2.

## Owner
Developer 1.

## Inputs
Preprocessed tiles from `ingestion/`.

## Outputs
FeatureCollection matching `shared-schemas/geojson/segmentation-output.schema.json`
Geometry in **EPSG:4326**.

Classes: `parcel`, `building`, `road`, `land_use`.

Communicate via GeoJSON files, not Python imports into Dev 2.

## Tests
`pytest ml-pipeline/segmentation/tests`

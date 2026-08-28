"""Discrepancy vs existing GIS record. Owner: Developer 3.

Do not import Dev 1 or Dev 2 implementation packages. Consume GeoJSON/API payloads only.
Metric comparisons must reproject from STORAGE_CRS to PROCESSING_CRS (env).
"""

from __future__ import annotations

import os


def storage_crs() -> str:
    return os.getenv("STORAGE_CRS", "EPSG:4326")


def processing_crs() -> str:
    return os.getenv("PROCESSING_CRS", "EPSG:32645")


def normalized_discrepancy(current_geojson: dict, existing_geojson: dict | None) -> float:
    """Return 0..1 discrepancy. Stub: 0.0 if no baseline. TODO(dev3): Hausdorff/area in PROCESSING_CRS."""
    if existing_geojson is None:
        return 0.0
    return 0.0

"""Raster to polygon. Owner: Dev 2. Metric ops in PROCESSING_CRS only."""

import os

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")
PROCESSING_CRS = os.getenv("PROCESSING_CRS", "EPSG:32645")


def raster_to_polygon(mask, transform, src_crs: str | None = None):
    """TODO(dev2): contour/polygonize then reproject to STORAGE_CRS for GeoJSON."""
    raise NotImplementedError("Dev 2: implement raster_to_polygon")

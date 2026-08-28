"""CRS-aware georeferencing stubs. Owner: Dev 1.

Always convert explicitly between STORAGE_CRS and PROCESSING_CRS.
Never mix lon/lat with metre calculations.
"""

import os

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")
PROCESSING_CRS = os.getenv("PROCESSING_CRS", "EPSG:32645")


def to_processing_crs(dataset) -> None:
    """TODO(dev1): reproject raster/vector to PROCESSING_CRS."""
    raise NotImplementedError("Dev 1: implement raster reprojection")


def to_storage_crs(dataset) -> None:
    """TODO(dev1): reproject results back to STORAGE_CRS before GeoJSON export."""
    raise NotImplementedError("Dev 1: implement storage CRS export")

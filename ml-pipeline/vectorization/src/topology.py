"""Topology validation. Owner: Dev 2. Run checks in PROCESSING_CRS (metres)."""

import os

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")
PROCESSING_CRS = os.getenv("PROCESSING_CRS", "EPSG:32645")


def validate_topology(polygons: list) -> dict:
    """TODO(dev2): overlaps, gaps, slivers. Return {valid, violations[]}."""
    raise NotImplementedError("Dev 2: implement topology validation")

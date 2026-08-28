"""Geometry helpers. Storage CRS is always EPSG:4326. Metric work must reproject to PROCESSING_CRS."""

from __future__ import annotations

import json
from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

from backend.api.app.config import settings


def storage_crs() -> str:
    return settings.storage_crs


def processing_crs() -> str:
    return settings.processing_crs


def geom_to_geojson(geom: WKBElement | BaseGeometry | None) -> dict | None:
    if geom is None:
        return None
    if isinstance(geom, BaseGeometry):
        return mapping(geom)
    return mapping(to_shape(geom))


def geojson_to_wkt(geojson: dict[str, Any]) -> str:
    g = shape(geojson)
    if not g.is_valid:
        raise ValueError("Invalid geometry")
    return g.wkt


def loads_geojson(geojson: dict[str, Any]) -> BaseGeometry:
    return shape(geojson)

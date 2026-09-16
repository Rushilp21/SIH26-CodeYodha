"""Georeferenced parcel-face extraction from boundary probabilities.

The boundary class is a line network. Polygonizing thresholded foreground
components produces building/edge fragments, not parcels. This module instead
closes small gaps in that network and polygonizes the enclosed background faces.
All filtering and simplification happen in the projected source raster CRS;
only the returned GeoJSON is converted to ``STORAGE_CRS``.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import rasterio.features
import torch
import torch.nn.functional as F
from pyproj import CRS, Transformer
from rasterio.transform import array_bounds
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import transform as transform_geometry

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")


@dataclass(frozen=True)
class VectorizationConfig:
    threshold: float = 0.35
    close_pixels: int = 5
    boundary_width_pixels: int = 1
    edge_buffer_pixels: int = 2
    min_area_m2: float = 20.0
    max_area_m2: float = 250_000.0
    simplify_tolerance_m: float = 0.25
    min_boundary_alignment: float = 0.0
    min_compactness: float = 0.0
    max_vertices: int = 10_000
    edge_weight: float = 0.0

    def validate(self) -> None:
        if not 0.0 < self.threshold < 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if self.close_pixels < 1 or self.close_pixels % 2 == 0:
            raise ValueError("close_pixels must be a positive odd integer")
        if self.boundary_width_pixels < 0 or self.edge_buffer_pixels < 0:
            raise ValueError("pixel widths cannot be negative")
        if not 0 <= self.min_boundary_alignment <= 1:
            raise ValueError("min_boundary_alignment must be between 0 and 1")
        if not 0 <= self.min_compactness <= 1:
            raise ValueError("min_compactness must be between 0 and 1")
        if self.max_vertices < 4:
            raise ValueError("max_vertices must be at least four")
        if not 0 <= self.edge_weight <= 1:
            raise ValueError("edge_weight must be between 0 and 1")
        if not 0 < self.min_area_m2 < self.max_area_m2:
            raise ValueError("invalid area limits")


def _morphological_close(mask: np.ndarray, kernel: int, width: int) -> np.ndarray:
    """Binary close and optional dilation using the existing Torch dependency."""
    tensor = torch.from_numpy(mask.astype(np.float32, copy=False))[None, None]
    if kernel > 1:
        padding = kernel // 2
        tensor = F.max_pool2d(tensor, kernel, stride=1, padding=padding)
        tensor = -F.max_pool2d(-tensor, kernel, stride=1, padding=padding)
    if width:
        kernel_width = 2 * width + 1
        tensor = F.max_pool2d(tensor, kernel_width, stride=1, padding=width)
    return tensor[0, 0].numpy() >= 0.5


def _sample_probability(probability: np.ndarray, transform, polygon: Polygon) -> float:
    pixel_size = max(abs(float(transform.a)), abs(float(transform.e)), 1e-6)
    count = max(48, min(512, int(polygon.length / pixel_size)))
    inverse = ~transform
    samples: list[float] = []
    for index in range(count):
        x, y = polygon.exterior.interpolate(index / count, normalized=True).coords[0]
        col, row = inverse @ (float(x), float(y))
        row_index, col_index = int(np.floor(row)), int(np.floor(col))
        if 0 <= row_index < probability.shape[0] and 0 <= col_index < probability.shape[1]:
            value = float(probability[row_index, col_index])
            if value >= 0:
                samples.append(value)
    return float(np.mean(samples)) if samples else 0.0


def _polygon_parts(geometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return []


def image_edge_evidence(image: np.ndarray, valid_mask: np.ndarray | None = None) -> np.ndarray:
    """Create robust, unit-scaled image-gradient evidence without changing georeferencing."""
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[0] < 3:
        raise ValueError("image must contain at least three band-first channels")
    rgb = image[:3].astype(np.float32, copy=False)
    gray = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    gradient_y, gradient_x = np.gradient(gray)
    magnitude = np.hypot(gradient_x, gradient_y)
    valid = np.isfinite(magnitude) if valid_mask is None else np.isfinite(magnitude) & valid_mask
    scale = float(np.percentile(magnitude[valid], 99)) if np.any(valid) else 0.0
    evidence = np.clip(magnitude / scale, 0.0, 1.0) if scale > 0 else np.zeros_like(magnitude)
    evidence[~valid] = 0.0
    return evidence.astype(np.float32, copy=False)


def raster_to_polygon(
    probability: np.ndarray,
    transform,
    src_crs: str,
    config: VectorizationConfig | None = None,
    edge_evidence: np.ndarray | None = None,
) -> dict[str, Any]:
    """Return an EPSG:4326 FeatureCollection of enclosed parcel candidates.

    Negative values are treated as nodata. Candidates touching the raster edge
    are excluded because their complete boundary lies outside the evidence grid.
    """
    config = config or VectorizationConfig()
    config.validate()
    probability = np.asarray(probability, dtype=np.float32)
    if probability.ndim != 2 or min(probability.shape) < 8:
        raise ValueError("probability must be a two-dimensional raster")
    source_crs = CRS.from_user_input(src_crs)
    if not source_crs.is_projected:
        raise ValueError("source raster CRS must be projected for metric vectorization")
    if transform.is_identity:
        raise ValueError("an affine geotransform is required")

    valid = np.isfinite(probability) & (probability >= 0)
    fused_probability = probability
    if config.edge_weight:
        if edge_evidence is None:
            raise ValueError("edge_evidence is required when edge_weight is non-zero")
        edge_evidence = np.asarray(edge_evidence, dtype=np.float32)
        if edge_evidence.shape != probability.shape:
            raise ValueError("edge_evidence must match the probability raster shape")
        fused_probability = (
            (1.0 - config.edge_weight) * np.clip(probability, 0.0, 1.0)
            + config.edge_weight * np.clip(edge_evidence, 0.0, 1.0)
        )
    boundary = valid & (fused_probability >= config.threshold)
    boundary = _morphological_close(boundary, config.close_pixels, config.boundary_width_pixels)
    open_faces = valid & ~boundary

    height, width = probability.shape
    west, south, east, north = array_bounds(height, width, transform)
    resolution = max(abs(float(transform.a)), abs(float(transform.e)))
    interior = box(west, south, east, north).buffer(-config.edge_buffer_pixels * resolution)
    to_storage = Transformer.from_crs(source_crs, STORAGE_CRS, always_xy=True).transform

    metric_candidates: list[tuple[Polygon, float]] = []
    for geometry, value in rasterio.features.shapes(
        open_faces.astype(np.uint8), mask=open_faces, transform=transform, connectivity=4
    ):
        if value != 1:
            continue
        for polygon in _polygon_parts(shape(geometry)):
            # A cadastral land face should not inherit foreground islands as holes.
            polygon = Polygon(polygon.exterior)
            if polygon.is_empty or not polygon.is_valid or not interior.contains(polygon):
                continue
            if not config.min_area_m2 <= polygon.area <= config.max_area_m2:
                continue
            simplified = polygon.simplify(config.simplify_tolerance_m, preserve_topology=True)
            if not isinstance(simplified, Polygon) or not simplified.is_valid or simplified.is_empty:
                simplified = polygon
            vertex_count = len(simplified.exterior.coords) - 1
            compactness = (
                float(4 * np.pi * simplified.area / (simplified.length ** 2))
                if simplified.length > 0 else 0.0
            )
            if vertex_count > config.max_vertices or compactness < config.min_compactness:
                continue
            alignment = _sample_probability(fused_probability, transform, simplified)
            if alignment < config.min_boundary_alignment:
                continue
            segformer_alignment = _sample_probability(probability, transform, simplified)
            metric_candidates.append((simplified, alignment, segformer_alignment))

    accepted: list[tuple[Polygon, float, float]] = []
    for candidate, alignment, segformer_alignment in sorted(metric_candidates, key=lambda item: item[0].area, reverse=True):
        if any(
            candidate.intersection(existing).area > 0.01
            for existing, _, _ in accepted
            if candidate.intersects(existing)
        ):
            continue
        accepted.append((candidate, alignment, segformer_alignment))

    features = []
    for index, (polygon, alignment, segformer_alignment) in enumerate(accepted):
        stored = transform_geometry(to_storage, polygon)
        if not stored.is_valid:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "class": "parcel",
                "candidate_index": index,
                # Preserve the upstream contract: raw_confidence is always the
                # frozen segmentation model's own score, never a fused score.
                "raw_confidence": segformer_alignment,
                "boundary_alignment_score": alignment,
                "segformer_boundary_alignment_score": segformer_alignment,
                "area_m2": float(polygon.area),
                "vertex_count": len(polygon.exterior.coords) - 1,
                "compactness": float(4 * np.pi * polygon.area / (polygon.length ** 2)) if polygon.length else 0.0,
                "vectorization": asdict(config),
            },
            "geometry": mapping(stored),
        })

    return {
        "type": "FeatureCollection",
        "name": "segformer_enclosed_parcel_faces",
        "crs": {"type": "name", "properties": {"name": STORAGE_CRS}},
        "features": features,
    }

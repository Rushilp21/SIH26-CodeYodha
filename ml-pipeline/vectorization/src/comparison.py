"""Reference-aware evaluation utilities. Reference geometry never enters inference."""

from __future__ import annotations

import statistics

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree


def _best_iou(source: list[Polygon], target: list[Polygon]) -> list[float]:
    if not source:
        return []
    if not target:
        return [0.0] * len(source)
    tree = STRtree(target)
    scores = []
    for geometry in source:
        best = 0.0
        for index in tree.query(geometry):
            other = target[int(index)]
            intersection = geometry.intersection(other).area
            if intersection <= 0:
                continue
            union = geometry.area + other.area - intersection
            best = max(best, intersection / union if union else 0.0)
        scores.append(float(best))
    return scores


def _sample_boundary(polygon: Polygon, count: int = 96) -> list[Point]:
    return [Point(polygon.exterior.interpolate(index / count, normalized=True)) for index in range(count)]


def _symmetric_boundary_distance(source: list[Polygon], target: list[Polygon]) -> list[float]:
    if not source or not target:
        return []
    tree = STRtree(target)
    distances = []
    for geometry in source:
        nearest = target[int(tree.nearest(geometry))]
        forward = statistics.mean(nearest.boundary.distance(point) for point in _sample_boundary(geometry))
        backward = statistics.mean(geometry.boundary.distance(point) for point in _sample_boundary(nearest))
        distances.append(float((forward + backward) / 2))
    return distances


def compare_polygon_sets(candidates: list[Polygon], references: list[Polygon]) -> dict:
    candidate_iou = _best_iou(candidates, references)
    reference_iou = _best_iou(references, candidates)
    precision = float(np.mean(candidate_iou)) if candidate_iou else 0.0
    recall = float(np.mean(reference_iou)) if reference_iou else 0.0
    harmonic = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    distances = _symmetric_boundary_distance(candidates, references)
    return {
        "candidate_count": len(candidates),
        "reference_count": len(references),
        "invalid_candidates": sum(not geometry.is_valid for geometry in candidates),
        "candidate_mean_best_iou": precision,
        "reference_mean_best_iou": recall,
        "harmonic_mean_best_iou": harmonic,
        "reference_matched_iou_50": sum(score >= 0.5 for score in reference_iou),
        "reference_matched_iou_75": sum(score >= 0.75 for score in reference_iou),
        "mean_symmetric_boundary_distance_m": float(np.mean(distances)) if distances else None,
        "median_candidate_area_m2": float(np.median([geometry.area for geometry in candidates])) if candidates else None,
        "median_reference_area_m2": float(np.median([geometry.area for geometry in references])) if references else None,
    }

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon

# Topology (overlap reduction) is the primary hackathon result for tonight's demo,
# so it dominates the weighted sum. Other weights are secondary, hand-tuned defaults.
WEIGHT_IOU = 1.0
WEIGHT_EDGE_ALIGNMENT = 1.0
WEIGHT_REGULARITY = 0.5
WEIGHT_TOPOLOGY = 2.0
WEIGHT_DEVIATION = 0.5


@dataclass
class RewardBreakdown:
    iou: float = 0.0
    edge_alignment: float = 0.0
    regularity: float = 0.0
    topology: float = 0.0
    baseline_deviation: float = 0.0
    total: float = 0.0


def _polygon_from_xy(vertices_xy) -> Polygon | None:
    verts = np.asarray(vertices_xy, dtype=np.float64)
    if verts.shape[0] < 3:
        return None
    poly = Polygon(verts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if (poly is not None and not poly.is_empty) else None


def compute_topology_term(current_polygon_xy, neighbor_polygons_xy) -> float:
    """Overlap penalty vs. neighboring parcels, normalized by own area.

    0.0 == no overlap with any neighbor. Grows with total overlap area relative
    to the parcel's own area, so it is comparable across differently-sized parcels.
    Same overlap definition as `vectorization.topology.validate_topology` (pairwise
    intersection area), computed directly on the metre-space env geometry instead
    of round-tripping through GeoJSON/CRS reprojection.
    """
    current = _polygon_from_xy(current_polygon_xy)
    if current is None or current.area <= 0:
        return 0.0

    total_overlap = 0.0
    for neighbor_xy in neighbor_polygons_xy:
        neighbor = _polygon_from_xy(neighbor_xy)
        if neighbor is None or not current.intersects(neighbor):
            continue
        total_overlap += current.intersection(neighbor).area

    return total_overlap / current.area


def compute_regularity_term(current_polygon_xy) -> float:
    """Penalize jagged / overly-complex boundaries.

    Combines two signals, averaged:
      - isoperimetric compactness deficit (1 - 4*pi*area/perimeter^2); 0 for a
        circle, growing toward 1 as the boundary gets more convoluted.
      - excess-vertex ratio vs. the convex hull's vertex count, i.e. how many
        more vertices the shape has than the simplest convex shape enclosing it.
    """
    current = _polygon_from_xy(current_polygon_xy)
    if current is None or current.area <= 0 or current.length <= 0:
        return 1.0

    compactness = (4 * math.pi * current.area) / (current.length ** 2)
    compactness = min(max(compactness, 0.0), 1.0)
    compactness_penalty = 1.0 - compactness

    hull = current.convex_hull
    if hull.geom_type == "Polygon":
        hull_vertex_count = max(len(hull.exterior.coords) - 1, 1)
    else:
        hull_vertex_count = 1
    current_vertex_count = len(np.asarray(current_polygon_xy))
    vertex_excess_ratio = max(0.0, current_vertex_count - hull_vertex_count) / hull_vertex_count
    vertex_excess_penalty = min(vertex_excess_ratio, 1.0)

    return 0.5 * compactness_penalty + 0.5 * vertex_excess_penalty


def compute_deviation_term(current_polygon_xy, original_polygon_xy) -> float:
    """Penalize drift from the pre-refinement geometry, scale-normalized.

    Vertex nudge actions preserve vertex count/order (see actions.py), so mean
    per-vertex Euclidean displacement is a cheap, exact stand-in for Hausdorff
    distance here. Normalized by the original parcel's characteristic radius
    (sqrt(area/pi)) so the penalty is comparable across differently-sized parcels.
    """
    current = np.asarray(current_polygon_xy, dtype=np.float64)
    original = np.asarray(original_polygon_xy, dtype=np.float64)
    if current.shape != original.shape:
        n = min(len(current), len(original))
        current, original = current[:n], original[:n]
    if len(current) == 0:
        return 0.0

    displacements = np.linalg.norm(current - original, axis=1)
    mean_displacement = float(np.mean(displacements))

    original_poly = _polygon_from_xy(original_polygon_xy)
    if original_poly is not None and original_poly.area > 0:
        scale = math.sqrt(original_poly.area / math.pi)
    else:
        scale = 1.0

    return mean_displacement / max(scale, 1e-6)


def compose_reward(
    iou_reward: float,
    edge_alignment_reward: float,
    geometry_regularization_penalty: float,
    topology_violation_penalty: float,
    baseline_deviation_penalty: float,
) -> RewardBreakdown:
    iou = WEIGHT_IOU * iou_reward
    edge_alignment = WEIGHT_EDGE_ALIGNMENT * edge_alignment_reward
    regularity = -WEIGHT_REGULARITY * geometry_regularization_penalty
    topology = -WEIGHT_TOPOLOGY * topology_violation_penalty
    baseline_deviation = -WEIGHT_DEVIATION * baseline_deviation_penalty
    total = iou + edge_alignment + regularity + topology + baseline_deviation
    return RewardBreakdown(
        iou=iou,
        edge_alignment=edge_alignment,
        regularity=regularity,
        topology=topology,
        baseline_deviation=baseline_deviation,
        total=total,
    )

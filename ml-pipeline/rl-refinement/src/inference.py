"""RL inference. Loads a trained per-parcel PPO policy, runs it over the
parcel's exterior boundary, and returns a refined geometry matching
shared-schemas/geojson/refined-parcel.schema.json. Not polygon smoothing:
every returned score traces back to a real reward term computed on the
policy's final geometry.
"""

from __future__ import annotations

import uuid

import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon, mapping, shape

from agent import ParcelBoundaryAgent, dedupe_ring
from environment import PROCESSING_CRS, STORAGE_CRS, ParcelBoundaryEnv
from reward import compute_deviation_term, compute_regularity_term, compute_topology_term

_TO_PROCESSING = Transformer.from_crs(STORAGE_CRS, PROCESSING_CRS, always_xy=True)
_TO_STORAGE = Transformer.from_crs(PROCESSING_CRS, STORAGE_CRS, always_xy=True)


def _project(coords, transformer) -> np.ndarray:
    xs, ys = transformer.transform([c[0] for c in coords], [c[1] for c in coords])
    return np.column_stack([xs, ys]).astype(np.float32)


def _clip01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def refine_parcel(payload: dict) -> dict:
    """Run a trained PPO policy over one parcel's exterior boundary.

    payload keys:
      geometry: GeoJSON Polygon, EPSG:4326 (STORAGE_CRS)
      model_path: path to this parcel's trained PPO .zip (see agent.train_on_parcels)
      parcel_id: optional str/uuid; generated if absent
      neighbor_geometries: list[GeoJSON geometry], EPSG:4326 (for the topology term)
      segmentation_score: optional float 0..1, passed through from the upstream
        segmentation model's own confidence (properties.raw_confidence upstream)
      max_steps / step_m: optional overrides; should match training config
    """
    geometry = payload["geometry"]
    model_path = payload["model_path"]
    parcel_id = payload.get("parcel_id") or str(uuid.uuid4())
    max_steps = payload.get("max_steps", 40)
    step_m = payload.get("step_m", 0.5)
    segmentation_score = _clip01(float(payload.get("segmentation_score", 0.0)))

    poly = shape(geometry)
    interiors_deg = [list(ring.coords) for ring in poly.interiors]

    initial_xy = dedupe_ring(_project(list(poly.exterior.coords), _TO_PROCESSING))
    neighbor_xy = [
        dedupe_ring(_project(list(shape(g).exterior.coords), _TO_PROCESSING))
        for g in payload.get("neighbor_geometries", [])
    ]

    env = ParcelBoundaryEnv(
        image_patch=None,
        elevation_patch=None,
        initial_polygon=initial_xy,
        neighboring_polygons=neighbor_xy,
        max_steps=max_steps,
        step_m=step_m,
    )
    agent = ParcelBoundaryAgent()
    agent.load(model_path, env=env)

    obs, _ = env.reset()
    terminated = truncated = False
    while not (terminated or truncated):
        action = agent.predict(obs)
        obs, _reward, terminated, truncated, _info = env.step(action)

    refined_xy = env._poly.copy()

    # Real reward terms on the *final* geometry -> explainability scores.
    topology_penalty = compute_topology_term(refined_xy, neighbor_xy)
    regularity_penalty = compute_regularity_term(refined_xy)
    deviation_penalty = compute_deviation_term(refined_xy, initial_xy)

    topology_score = _clip01(1.0 - topology_penalty)
    regularity_score = _clip01(1.0 - regularity_penalty)
    deviation_from_baseline_score = _clip01(1.0 - deviation_penalty)
    # TODO post-hackathon: needs image gradients / labeled ground truth
    edge_alignment_score = 0.0

    confidence_score = _clip01(
        0.6 * topology_score + 0.25 * deviation_from_baseline_score + 0.15 * regularity_score
    )

    refined_deg = np.column_stack(_TO_STORAGE.transform(refined_xy[:, 0], refined_xy[:, 1]))
    refined_ring_deg = np.vstack([refined_deg, refined_deg[0]])  # re-close ring
    refined_polygon = Polygon(refined_ring_deg, holes=interiors_deg)
    repaired = False
    if not refined_polygon.is_valid:
        refined_polygon = refined_polygon.buffer(0)
        repaired = True

    explanation = (
        f"PPO policy nudged {len(refined_xy)} boundary vertices over up to {max_steps} steps. "
        f"Overlap-with-neighbors penalty {topology_penalty:.3f} -> topology_score {topology_score:.2f}. "
        f"Mean vertex displacement from baseline {deviation_penalty:.3f} (scale-normalized) -> "
        f"deviation_from_baseline_score {deviation_from_baseline_score:.2f}. "
        f"Shape regularity penalty {regularity_penalty:.3f} -> regularity_score {regularity_score:.2f}. "
        + ("Geometry required a validity repair (buffer(0)) after refinement. " if repaired else "")
        + "IoU (segmentation_score beyond pass-through) and edge_alignment_score not computed this "
        "pass. TODO post-hackathon: needs image gradients / labeled ground truth."
    )

    return {
        "parcel_id": parcel_id,
        "geometry": mapping(refined_polygon),
        "confidence_score": confidence_score,
        "segmentation_score": segmentation_score,
        "topology_score": topology_score,
        "edge_alignment_score": edge_alignment_score,
        "deviation_from_baseline_score": deviation_from_baseline_score,
        "regularity_score": regularity_score,
        "explanation": explanation,
        "demo": True,
    }

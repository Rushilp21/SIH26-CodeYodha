from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ParcelState:
    """Conceptual RL state (not a full raster encoder yet)."""

    image_patch: np.ndarray | None
    elevation_patch: np.ndarray | None
    current_polygon_xy: np.ndarray  # (V, 2) in PROCESSING_CRS metres when wired
    neighbor_polygons: list[np.ndarray]
    topology_flags: dict


MAX_VERTICES = 40
OBS_SIZE = MAX_VERTICES * 2


def flatten_observation(state: ParcelState) -> np.ndarray:
    verts = np.asarray(state.current_polygon_xy, dtype=np.float32)
    # Center on the polygon's own centroid: current_polygon_xy arrives in
    # PROCESSING_CRS (UTM) metres, e.g. easting/northing ~1e5-1e6, which would
    # otherwise be fed raw into the policy MLP (and even exceeds the +/-1e6
    # observation_space bound in environment.py). Centering keeps the network
    # seeing small, well-scaled relative vertex positions.
    if verts.size:
        verts = verts - verts.mean(axis=0)
    flat = verts.reshape(-1)
    # Fixed-size scaffold observation: first MAX_VERTICES vertex coords + zeros
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    n = min(flat.size, OBS_SIZE)
    obs[:n] = flat[:n]
    return obs

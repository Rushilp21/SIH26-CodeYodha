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


def flatten_observation(state: ParcelState) -> np.ndarray:
    verts = state.current_polygon_xy.reshape(-1).astype(np.float32)
    # Fixed-size scaffold observation: first 32 vertex coords + zeros
    obs = np.zeros(64, dtype=np.float32)
    n = min(verts.size, 32)
    obs[:n] = verts[:n]
    return obs

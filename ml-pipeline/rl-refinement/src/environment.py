"""Gymnasium-compatible parcel boundary environment skeleton.

This is NOT trained PPO and NOT smoothing. Vertex nudges only.
"""

from __future__ import annotations

import os

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:  # scaffold still importable without gym installed
    gym = None
    spaces = None

from actions import DIRECTIONS, action_space_n, decode_action
from reward import RewardBreakdown, compose_reward
from state import ParcelState, flatten_observation

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")
PROCESSING_CRS = os.getenv("PROCESSING_CRS", "EPSG:32645")


class ParcelBoundaryEnv(gym.Env if gym else object):
    metadata = {"render_modes": []}

    def __init__(
        self,
        image_patch,
        elevation_patch,
        initial_polygon,
        neighboring_polygons=None,
        ground_truth=None,
        step_m: float = 0.5,
        max_steps: int = 50,
    ):
        super().__init__() if gym else None
        self.image_patch = image_patch
        self.elevation_patch = elevation_patch
        self.initial_polygon = np.asarray(initial_polygon, dtype=np.float32)
        if self.initial_polygon.ndim != 2 or self.initial_polygon.shape[1] != 2:
            raise ValueError("initial_polygon must be (V, 2) in PROCESSING_CRS metres")
        self.neighboring_polygons = neighboring_polygons or []
        self.ground_truth = ground_truth
        self.step_m = step_m
        self.max_steps = max_steps
        self._t = 0
        self._poly = self.initial_polygon.copy()
        self.last_breakdown = RewardBreakdown()

        n = action_space_n(len(self.initial_polygon))
        if spaces:
            self.action_space = spaces.Discrete(n)
            self.observation_space = spaces.Box(low=-1e6, high=1e6, shape=(64,), dtype=np.float32)
        else:
            self.action_space = type("A", (), {"n": n})()
            self.observation_space = type("O", (), {"shape": (64,)})()

    def reset(self, seed=None, options=None):
        if gym:
            super().reset(seed=seed)
        self._t = 0
        self._poly = self.initial_polygon.copy()
        obs = self._get_observation()
        return obs, {}

    def step(self, action):
        vertex, direction = decode_action(int(action), len(self._poly))
        dx, dy = DIRECTIONS[direction]
        self._poly[vertex, 0] += dx * self.step_m
        self._poly[vertex, 1] += dy * self.step_m
        self._t += 1
        reward_bd = self._calculate_reward()
        self.last_breakdown = reward_bd
        terminated = False
        truncated = self._t >= self.max_steps
        info = {"reward_breakdown": reward_bd, "processing_crs": PROCESSING_CRS}
        return self._get_observation(), reward_bd.total, terminated, truncated, info

    def _get_observation(self):
        state = ParcelState(
            image_patch=self.image_patch,
            elevation_patch=self.elevation_patch,
            current_polygon_xy=self._poly,
            neighbor_polygons=self.neighboring_polygons,
            topology_flags={},
        )
        return flatten_observation(state)

    def _calculate_reward(self) -> RewardBreakdown:
        """Scaffold zeros except a tiny regularity placeholder. Dev 2 fills real terms."""
        iou_reward = 0.0
        edge_alignment_reward = 0.0
        geometry_regularization_penalty = 0.0
        topology_violation_penalty = 0.0
        baseline_deviation_penalty = 0.0
        if self.ground_truth is None:
            pass
        return compose_reward(
            iou_reward,
            edge_alignment_reward,
            geometry_regularization_penalty,
            topology_violation_penalty,
            baseline_deviation_penalty,
        )

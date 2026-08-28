"""PPO agent for boundary refinement, built on Stable-Baselines3."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from environment import ParcelBoundaryEnv

DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def dedupe_ring(vertices_xy) -> np.ndarray:
    """Drop a GeoJSON-style closing vertex (first == last) before feeding a
    ring into the env: vertex-nudge actions move indices independently, so a
    duplicated closing point would let the ring split into a gap."""
    verts = np.asarray(vertices_xy, dtype=np.float32)
    if len(verts) > 1 and np.allclose(verts[0], verts[-1]):
        verts = verts[:-1]
    return verts


class ParcelBoundaryAgent:
    def __init__(self, env=None):
        self.env = env
        self.algo = "PPO"
        self.library = "stable-baselines3"
        self.trained = False
        self.model = None

    def train(self, total_timesteps: int = 256) -> None:
        if self.env is None:
            raise ValueError("env is required to train")
        n_steps = min(total_timesteps, max(getattr(self.env, "max_steps", 32), 8))
        batch_size = max(n_steps // 2, 1)
        self.model = PPO(
            "MlpPolicy",
            self.env,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=4,
            verbose=0,
        )
        self.model.learn(total_timesteps=total_timesteps)
        self.trained = True

    def predict(self, observation):
        if self.model is None:
            raise RuntimeError("Agent has no trained/loaded model")
        action, _ = self.model.predict(observation, deterministic=True)
        return int(action)

    def save(self, path) -> None:
        if self.model is None:
            raise RuntimeError("Nothing to save: model has not been trained")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(str(path))

    def load(self, path, env=None) -> None:
        self.env = env or self.env
        self.model = PPO.load(str(path), env=self.env)
        self.trained = True


def train_on_parcels(
    parcels_xy: list,
    models_dir="__default__",
    timesteps_per_parcel: int = 256,
    max_steps: int = 40,
    step_m: float = 0.5,
) -> list:
    """Train one lightweight PPO policy per parcel.

    Each parcel's action space is Discrete(n_vertices * 4), so vertex count
    varies parcel-to-parcel and a single shared policy across all 15 would
    need action-space padding + masking. Out of scope tonight: a dedicated
    small model per parcel is simpler and still real PPO, not fake weights.
    Each env is given every *other* parcel (original geometry) as fixed
    neighbor context so the topology/overlap reward term is meaningful.
    """
    if models_dir == "__default__":
        models_dir = DEFAULT_MODELS_DIR
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    dedup = [dedupe_ring(p) for p in parcels_xy]
    results = []
    for idx, poly in enumerate(dedup):
        neighbors = [p for j, p in enumerate(dedup) if j != idx]
        env = ParcelBoundaryEnv(
            image_patch=None,
            elevation_patch=None,
            initial_polygon=poly,
            neighboring_polygons=neighbors,
            max_steps=max_steps,
            step_m=step_m,
        )
        agent = ParcelBoundaryAgent(env)
        agent.train(total_timesteps=timesteps_per_parcel)
        model_path = models_dir / f"parcel_{idx:02d}_ppo.zip"
        agent.save(model_path)
        results.append(
            {
                "parcel_index": idx,
                "n_vertices": len(poly),
                "model_path": str(model_path),
                "final_reward_breakdown": env.last_breakdown,
            }
        )
    return results

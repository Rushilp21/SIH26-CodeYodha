"""PPO agent placeholder. Do NOT fake training.

TODO(dev2):
  from stable_baselines3 import PPO
  model = PPO("MlpPolicy", env, verbose=1)
  model.learn(total_timesteps=...)
"""

from __future__ import annotations


class ParcelBoundaryAgent:
    def __init__(self, env=None):
        self.env = env
        self.algo = "PPO"
        self.library = "stable-baselines3"
        self.trained = False
        self.model = None

    def train(self, total_timesteps: int = 0) -> None:
        raise NotImplementedError(
            "Dev 2: wire Stable-Baselines3 PPO. Do not check in fake weights."
        )

    def predict(self, observation):
        raise NotImplementedError("Dev 2: implement after training")

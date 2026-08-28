import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from environment import ParcelBoundaryEnv  # noqa: E402


def test_reset_and_step():
    poly = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    env = ParcelBoundaryEnv(None, None, poly)
    obs, info = env.reset()
    assert obs.shape == (64,)
    obs2, reward, term, trunc, info = env.step(0)
    assert "reward_breakdown" in info
    assert info["reward_breakdown"].total == reward

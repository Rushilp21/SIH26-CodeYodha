import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from health_score import compute_health_score, DEFAULT_WEIGHTS  # noqa: E402


def test_default_weights_sum_to_one():
    w = DEFAULT_WEIGHTS
    assert abs((w.w1 + w.w2 + w.w3 + w.w4) - 1.0) < 1e-9


def test_perfect_inputs():
    assert compute_health_score(1.0, 0.0, 0.0, 0.0) == 1.0

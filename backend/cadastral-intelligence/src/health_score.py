"""Cadastral health score — frozen formula. Owner: Developer 3.

health_score =
    w1 * confidence_score
    + w2 * (1 - topology_violation_flag)
    + w3 * (1 - normalized_discrepancy_vs_existing_record)
    + w4 * (1 - historical_volatility)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HealthWeights:
    w1: float = 0.4
    w2: float = 0.2
    w3: float = 0.2
    w4: float = 0.2


DEFAULT_WEIGHTS = HealthWeights()


def compute_health_score(
    confidence_score: float,
    topology_violation_flag: float,
    normalized_discrepancy_vs_existing_record: float,
    historical_volatility: float,
    weights: HealthWeights | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    score = (
        w.w1 * confidence_score
        + w.w2 * (1 - topology_violation_flag)
        + w.w3 * (1 - normalized_discrepancy_vs_existing_record)
        + w.w4 * (1 - historical_volatility)
    )
    return max(0.0, min(1.0, score))

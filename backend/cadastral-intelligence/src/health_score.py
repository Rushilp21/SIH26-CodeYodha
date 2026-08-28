"""Cadastral health score — frozen formula. Owner: Developer 3.

health_score =
    w1 * confidence_score
    + w2 * (1 - topology_violation_flag)
    + w3 * (1 - normalized_discrepancy_vs_existing_record)
    + w4 * (1 - historical_volatility)
"""
from dataclasses import dataclass

from .config import settings


@dataclass
class HealthScoreInput:
    confidence_score: float
    topology_violation_flag: bool
    normalized_discrepancy: float
    historical_volatility: float


@dataclass
class HealthScoreResult:
    score: float
    band: str
    explanation: str


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def calculate_health_score(
    data: HealthScoreInput,
) -> HealthScoreResult:

    confidence = clamp(data.confidence_score)

    topology_validity = (
        0.0
        if data.topology_violation_flag
        else 1.0
    )

    discrepancy_reliability = 1.0 - clamp(
        data.normalized_discrepancy
    )

    historical_reliability = 1.0 - clamp(
        data.historical_volatility
    )

    score = (
        settings.health_weight_confidence * confidence
        + settings.health_weight_topology * topology_validity
        + settings.health_weight_discrepancy * discrepancy_reliability
        + settings.health_weight_history * historical_reliability
    )

    score = round(clamp(score), 4)

    if score >= 0.85:
        band = "high"
    elif score >= 0.60:
        band = "medium"
    else:
        band = "low"

    explanation = (
        f"Health score {score:.2f}: "
        f"confidence={confidence:.2f}, "
        f"topology={'valid' if topology_validity else 'violation'}, "
        f"discrepancy={data.normalized_discrepancy:.2f}, "
        f"historical_volatility={data.historical_volatility:.2f}."
    )

    return HealthScoreResult(
        score=score,
        band=band,
        explanation=explanation,
    )
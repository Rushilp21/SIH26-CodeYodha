"""Survey prioritization. Owner: Developer 3."""


from dataclasses import dataclass


@dataclass
class PriorityResult:
    priority_score: float
    reason: str


def calculate_priority(
    confidence_score: float,
    normalized_discrepancy: float,
    historical_volatility: float,
    anomaly_count: int,
    topology_violation: bool,
) -> PriorityResult:

    confidence_risk = 1.0 - max(
        0.0,
        min(1.0, confidence_score)
    )

    discrepancy_risk = max(
        0.0,
        min(1.0, normalized_discrepancy)
    )

    historical_risk = max(
        0.0,
        min(1.0, historical_volatility)
    )

    anomaly_risk = min(
        1.0,
        anomaly_count / 3.0
    )

    topology_risk = (
        1.0
        if topology_violation
        else 0.0
    )

    priority = (
        0.40 * confidence_risk
        + 0.25 * discrepancy_risk
        + 0.15 * historical_risk
        + 0.10 * anomaly_risk
        + 0.10 * topology_risk
    )

    priority = round(
        max(0.0, min(1.0, priority)),
        4
    )

    reasons = []

    if confidence_score < 0.60:
        reasons.append("low confidence")

    if normalized_discrepancy >= 0.30:
        reasons.append("historical/record discrepancy")

    if historical_volatility >= 0.50:
        reasons.append("historical instability")

    if anomaly_count > 0:
        reasons.append(f"{anomaly_count} anomaly(s)")

    if topology_violation:
        reasons.append("topology violation")

    reason = (
        ", ".join(reasons)
        if reasons
        else "low-risk parcel; routine review"
    )

    return PriorityResult(
        priority_score=priority,
        reason=reason,
    )
"""Survey prioritization. Owner: Developer 3."""


def priority_score(confidence_score: float, health_score: float, anomaly_magnitude: float = 0.0) -> float:
    """Higher = more urgent. Inverse confidence, inverse health, plus anomalies."""
    return round((1.0 - confidence_score) * 0.5 + (1.0 - health_score) * 0.3 + anomaly_magnitude * 0.2, 4)

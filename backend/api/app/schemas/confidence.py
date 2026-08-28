HIGH_MIN = 0.85
MEDIUM_MIN = 0.60


def confidence_band(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= HIGH_MIN:
        return "HIGH"
    if score >= MEDIUM_MIN:
        return "MEDIUM"
    return "LOW"

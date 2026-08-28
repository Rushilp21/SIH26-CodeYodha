from src.health_score import (
    HealthScoreInput,
    calculate_health_score,
)


def test_perfect_health_score():

    result = calculate_health_score(
        HealthScoreInput(
            confidence_score=1.0,
            topology_violation_flag=False,
            normalized_discrepancy=0.0,
            historical_volatility=0.0,
        )
    )

    assert result.score == 1.0
    assert result.band == "high"


def test_bad_health_score():

    result = calculate_health_score(
        HealthScoreInput(
            confidence_score=0.2,
            topology_violation_flag=True,
            normalized_discrepancy=1.0,
            historical_volatility=1.0,
        )
    )

    assert result.score == 0.08
    assert result.band == "low"


def test_medium_health_score():

    result = calculate_health_score(
        HealthScoreInput(
            confidence_score=0.8,
            topology_violation_flag=False,
            normalized_discrepancy=0.4,
            historical_volatility=0.2,
        )
    )

    assert 0.60 <= result.score <= 0.85
from src.prioritization import calculate_priority


def test_low_confidence_has_high_priority():

    result = calculate_priority(
        confidence_score=0.30,
        normalized_discrepancy=0.70,
        historical_volatility=0.60,
        anomaly_count=2,
        topology_violation=True,
    )

    assert result.priority_score > 0.5


def test_good_parcel_has_low_priority():

    result = calculate_priority(
        confidence_score=0.95,
        normalized_discrepancy=0.02,
        historical_volatility=0.01,
        anomaly_count=0,
        topology_violation=False,
    )

    assert result.priority_score < 0.1
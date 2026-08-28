"""Anomaly detection stubs. Types: boundary_shift, overlap, encroachment, topology_break."""

ANOMALY_TYPES = ("boundary_shift", "overlap", "encroachment", "topology_break")


from dataclasses import dataclass


@dataclass
class Anomaly:
    anomaly_type: str
    magnitude: float
    explanation: str


def detect_anomalies(
    confidence_score: float,
    normalized_discrepancy: float,
    topology_violation: bool,
    historical_volatility: float,
) -> list[Anomaly]:

    anomalies = []

    # 1. Low-confidence anomaly
    if confidence_score < 0.60:
        anomalies.append(
            Anomaly(
                anomaly_type="boundary_shift",
                magnitude=round(
                    1.0 - confidence_score,
                    4
                ),
                explanation=(
                    f"Low AI/RL confidence "
                    f"({confidence_score:.2f}); "
                    "parcel requires field verification."
                ),
            )
        )

    # 2. Historical / existing-record discrepancy
    if normalized_discrepancy >= 0.30:
        anomalies.append(
            Anomaly(
                anomaly_type="boundary_shift",
                magnitude=round(
                    normalized_discrepancy,
                    4
                ),
                explanation=(
                    "Current parcel geometry differs "
                    "significantly from the existing/historical "
                    "record."
                ),
            )
        )

    # 3. Topology
    if topology_violation:
        anomalies.append(
            Anomaly(
                anomaly_type="topology_break",
                magnitude=1.0,
                explanation=(
                    "Parcel contains a topology violation "
                    "such as invalid geometry or overlap."
                ),
            )
        )

    # 4. Historical volatility
    if historical_volatility >= 0.50:
        anomalies.append(
            Anomaly(
                anomaly_type="encroachment",
                magnitude=round(
                    historical_volatility,
                    4
                ),
                explanation=(
                    "Parcel shows substantial historical "
                    "boundary/area volatility."
                ),
            )
        )

    return anomalies
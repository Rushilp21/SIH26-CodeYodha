from .database import fetch_one, execute
from .health_score import (
    HealthScoreInput,
    calculate_health_score,
)
from .discrepancy import calculate_discrepancy
from .anomaly_detection import detect_anomalies
from .prioritization import calculate_priority


def get_parcel(parcel_id: str):

    query = """
        SELECT
            id,
            project_id,
            ST_AsGeoJSON(geom)::json AS geometry,
            confidence_score,
            health_score,
            status
        FROM parcels
        WHERE id = :parcel_id
    """

    return fetch_one(
        query,
        {"parcel_id": parcel_id}
    )


def get_latest_version(parcel_id: str):

    query = """
        SELECT
            id,
            ST_AsGeoJSON(geom)::json AS geometry,
            captured_at,
            source
        FROM parcel_versions
        WHERE parcel_id = :parcel_id
        ORDER BY captured_at DESC
        LIMIT 1
    """

    return fetch_one(
        query,
        {"parcel_id": parcel_id}
    )


def check_topology(parcel_id: str) -> bool:

    query = """
        SELECT EXISTS (
            SELECT 1
            FROM parcels p
            WHERE p.id = :parcel_id
              AND NOT ST_IsValid(p.geom)
        )
        OR EXISTS (
            SELECT 1
            FROM parcels p
            JOIN parcels n
              ON p.project_id = n.project_id
             AND p.id <> n.id
             AND ST_Overlaps(p.geom, n.geom)
            WHERE p.id = :parcel_id
        ) AS violation
    """

    result = fetch_one(
        query,
        {"parcel_id": parcel_id}
    )

    return bool(result["violation"])


def get_historical_volatility(parcel_id: str) -> float:

    query = """
        WITH versions AS (
            SELECT
                geom,
                captured_at,
                LAG(geom) OVER (
                    ORDER BY captured_at
                ) AS previous_geom
            FROM parcel_versions
            WHERE parcel_id = :parcel_id
        )
        SELECT COALESCE(
            AVG(
                LEAST(
                    1.0,
                    ABS(
                        ST_Area(geom::geography)
                        -
                        ST_Area(previous_geom::geography)
                    )
                    /
                    NULLIF(
                        ST_Area(previous_geom::geography),
                        0
                    )
                )
            ),
            0
        ) AS volatility
        FROM versions
        WHERE previous_geom IS NOT NULL
    """

    result = fetch_one(
        query,
        {"parcel_id": parcel_id}
    )

    return float(
        result["volatility"] or 0.0
    )


def analyze_parcel(parcel_id: str):

    parcel = get_parcel(parcel_id)

    if not parcel:
        raise ValueError(
            f"Parcel {parcel_id} not found"
        )

    confidence = float(
        parcel["confidence_score"] or 0.0
    )

    topology_violation = check_topology(
        parcel_id
    )

    historical_volatility = (
        get_historical_volatility(
            parcel_id
        )
    )

    latest_version = get_latest_version(
        parcel_id
    )

    normalized_discrepancy = 0.0
    discrepancy_result = None

    if latest_version:

        discrepancy_result = calculate_discrepancy(
            parcel["geometry"],
            latest_version["geometry"],
        )

        normalized_discrepancy = (
            discrepancy_result.normalized_discrepancy
        )

    health_result = calculate_health_score(
        HealthScoreInput(
            confidence_score=confidence,
            topology_violation_flag=topology_violation,
            normalized_discrepancy=normalized_discrepancy,
            historical_volatility=historical_volatility,
        )
    )

    anomalies = detect_anomalies(
        confidence_score=confidence,
        normalized_discrepancy=normalized_discrepancy,
        topology_violation=topology_violation,
        historical_volatility=historical_volatility,
    )

    priority = calculate_priority(
        confidence_score=confidence,
        normalized_discrepancy=normalized_discrepancy,
        historical_volatility=historical_volatility,
        anomaly_count=len(anomalies),
        topology_violation=topology_violation,
    )

    # Write health score
    execute(
        """
        UPDATE parcels
        SET health_score = :health_score,
            updated_at = NOW()
        WHERE id = :parcel_id
        """,
        {
            "health_score": health_result.score,
            "parcel_id": parcel_id,
        },
    )

    # Write anomalies
    for anomaly in anomalies:

        execute(
            """
            INSERT INTO anomalies (
                parcel_id,
                type,
                magnitude,
                detected_at
            )
            VALUES (
                :parcel_id,
                :type,
                :magnitude,
                NOW()
            )
            """,
            {
                "parcel_id": parcel_id,
                "type": anomaly.anomaly_type,
                "magnitude": anomaly.magnitude,
            },
        )

    # Write survey queue
    execute(
        """
        INSERT INTO survey_queue (
            parcel_id,
            priority_score,
            reason,
            status,
            created_at
        )
        VALUES (
            :parcel_id,
            :priority_score,
            :reason,
            'pending',
            NOW()
        )
        """,
        {
            "parcel_id": parcel_id,
            "priority_score": priority.priority_score,
            "reason": priority.reason,
        },
    )

    return {
        "parcel_id": str(parcel_id),
        "confidence_score": confidence,
        "health_score": health_result.score,
        "health_band": health_result.band,
        "topology_violation": topology_violation,
        "historical_volatility": round(
            historical_volatility,
            4
        ),
        "normalized_discrepancy": round(
            normalized_discrepancy,
            4
        ),
        "discrepancy": (
            discrepancy_result.__dict__
            if discrepancy_result
            else None
        ),
        "anomalies": [
            anomaly.__dict__
            for anomaly in anomalies
        ],
        "survey_priority": priority.__dict__,
        "health_explanation": (
            health_result.explanation
        ),
    }
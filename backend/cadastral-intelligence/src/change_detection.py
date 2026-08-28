"""Historical change detection. Owner: Developer 3. Stub only — do not claim live ML."""


from dataclasses import dataclass
from datetime import datetime

from .database import fetch_all


@dataclass
class HistoricalChange:
    parcel_id: str
    captured_at: datetime | None
    source: str | None
    normalized_discrepancy: float
    area_change_ratio: float
    explanation: str


def get_historical_versions(parcel_id: str):

    query = """
        SELECT
            id,
            parcel_id,
            ST_AsGeoJSON(geom)::json AS geometry,
            captured_at,
            source
        FROM parcel_versions
        WHERE parcel_id = :parcel_id
        ORDER BY captured_at ASC
    """

    return fetch_all(
        query,
        {"parcel_id": parcel_id}
    )


def detect_historical_changes(parcel_id: str):

    versions = get_historical_versions(parcel_id)

    if len(versions) < 2:
        return []

    changes = []

    for previous, current in zip(
        versions[:-1],
        versions[1:]
    ):

        previous_area = get_area(
            previous["geometry"]
        )

        current_area = get_area(
            current["geometry"]
        )

        area_change_ratio = abs(
            current_area - previous_area
        ) / max(previous_area, 1e-9)

        discrepancy = min(
            1.0,
            area_change_ratio
        )

        if discrepancy >= 0.6:
            severity = "high"
        elif discrepancy >= 0.3:
            severity = "medium"
        else:
            severity = "low"

        explanation = (
            f"{severity.capitalize()} historical change: "
            f"parcel area changed by "
            f"{area_change_ratio:.2%} between "
            f"{previous['captured_at']} and "
            f"{current['captured_at']}."
        )

        changes.append(
            HistoricalChange(
                parcel_id=str(parcel_id),
                captured_at=current["captured_at"],
                source=current["source"],
                normalized_discrepancy=round(
                    discrepancy,
                    4
                ),
                area_change_ratio=round(
                    area_change_ratio,
                    4
                ),
                explanation=explanation,
            )
        )

    return changes


def get_area(geojson: dict) -> float:
    from shapely.geometry import shape

    return shape(geojson).area
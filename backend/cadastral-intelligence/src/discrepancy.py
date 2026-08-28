"""Discrepancy vs existing GIS record. Owner: Developer 3.

Do not import Dev 1 or Dev 2 implementation packages. Consume GeoJSON/API payloads only.
Metric comparisons must reproject from STORAGE_CRS to PROCESSING_CRS (env).
"""

from dataclasses import dataclass
from shapely.geometry import shape


@dataclass
class DiscrepancyResult:
    normalized_discrepancy: float
    area_difference_ratio: float
    boundary_difference_ratio: float
    centroid_shift_m: float
    explanation: str


def calculate_discrepancy(
    current_geojson: dict,
    historical_geojson: dict,
) -> DiscrepancyResult:

    current = shape(current_geojson)
    historical = shape(historical_geojson)

    if not current.is_valid:
        current = current.buffer(0)

    if not historical.is_valid:
        historical = historical.buffer(0)

    historical_area = max(historical.area, 1e-9)

    area_difference_ratio = abs(
        current.area - historical.area
    ) / historical_area

    union_area = current.union(historical).area

    if union_area > 0:
        boundary_difference_ratio = (
            current.symmetric_difference(historical).area
            / union_area
        )
    else:
        boundary_difference_ratio = 0.0

    centroid_shift = current.centroid.distance(
        historical.centroid
    )

    normalized_discrepancy = min(
        1.0,
        (
            0.4 * min(area_difference_ratio, 1.0)
            + 0.6 * min(boundary_difference_ratio, 1.0)
        )
    )

    if normalized_discrepancy >= 0.6:
        severity = "high"
    elif normalized_discrepancy >= 0.3:
        severity = "medium"
    else:
        severity = "low"

    explanation = (
        f"{severity.capitalize()} discrepancy detected: "
        f"area difference={area_difference_ratio:.2%}, "
        f"boundary difference={boundary_difference_ratio:.2%}, "
        f"centroid shift={centroid_shift:.2f} processing units."
    )

    return DiscrepancyResult(
        normalized_discrepancy=round(
            normalized_discrepancy,
            4
        ),
        area_difference_ratio=round(
            area_difference_ratio,
            4
        ),
        boundary_difference_ratio=round(
            boundary_difference_ratio,
            4
        ),
        centroid_shift_m=round(
            centroid_shift,
            3
        ),
        explanation=explanation,
    )
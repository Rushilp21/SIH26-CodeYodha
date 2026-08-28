"""Topology validation. Owner: Dev 2. Run checks in PROCESSING_CRS (metres)."""

import json
import os
import statistics

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform
from shapely.validation import explain_validity

STORAGE_CRS = os.getenv("STORAGE_CRS", "EPSG:4326")
PROCESSING_CRS = os.getenv("PROCESSING_CRS", "EPSG:32645")

SLIVER_AREA_RATIO = 0.05
OVERLAP_AREA_EPSILON_SQM = 1.0  # overlaps smaller than this are boundary-touch noise, not real overlap


def _to_geometry(item):
    if hasattr(item, "geom_type"):
        return item
    if isinstance(item, dict):
        geom = item["geometry"] if item.get("type") == "Feature" else item
        return shape(geom)
    raise TypeError(f"Unsupported polygon input type: {type(item)!r}")


def _to_processing_crs(geometries):
    transformer = Transformer.from_crs(STORAGE_CRS, PROCESSING_CRS, always_xy=True)
    return [shapely_transform(transformer.transform, geom) for geom in geometries]


def validate_topology(polygons: list) -> dict:
    """Check validity, pairwise overlaps, and sliver artifacts.

    `polygons` may be Shapely geometries or GeoJSON features/geometries (mixed is fine).
    Metric checks (area, overlap) run in PROCESSING_CRS since `polygons` are assumed to be
    in STORAGE_CRS (degrees), where raw Shapely .area is not a meaningful area measure.
    """
    geometries = [_to_geometry(p) for p in polygons]
    metric_geometries = _to_processing_crs(geometries)

    violations = []

    for idx, geom in enumerate(metric_geometries):
        if not geom.is_valid:
            violations.append({
                "feature_index": idx,
                "type": "invalid_geometry",
                "detail": explain_validity(geom),
            })

    valid_areas = [geom.area for geom in metric_geometries if geom.is_valid]
    if valid_areas:
        median_area = statistics.median(valid_areas)
        sliver_threshold = median_area * SLIVER_AREA_RATIO
        for idx, geom in enumerate(metric_geometries):
            if not geom.is_valid:
                continue
            if geom.area < sliver_threshold:
                violations.append({
                    "feature_index": idx,
                    "type": "sliver",
                    "detail": (
                        f"area={geom.area:.2f} sq m is below {SLIVER_AREA_RATIO:.0%} of "
                        f"median parcel area ({median_area:.2f} sq m)"
                    ),
                })

    n = len(metric_geometries)
    for i in range(n):
        geom_i = metric_geometries[i]
        if not geom_i.is_valid:
            continue
        for j in range(i + 1, n):
            geom_j = metric_geometries[j]
            if not geom_j.is_valid or not geom_i.intersects(geom_j):
                continue
            overlap_area = geom_i.intersection(geom_j).area
            if overlap_area > OVERLAP_AREA_EPSILON_SQM:
                violations.append({
                    "feature_index": i,
                    "type": "overlap",
                    "detail": f"overlaps feature {j} by {overlap_area:.2f} sq m",
                })

    return {
        "valid": len(violations) == 0,
        "violations": violations,
    }


if __name__ == "__main__":
    with open("data/raw/segmentation/parcels_simplified.geojson", "r", encoding="utf-8") as f:
        collection = json.load(f)

    report = validate_topology(collection["features"])

    print(f"valid: {report['valid']}")
    print(f"violations: {len(report['violations'])}")
    for v in report["violations"]:
        print(f"  feature {v['feature_index']} [{v['type']}]: {v['detail']}")

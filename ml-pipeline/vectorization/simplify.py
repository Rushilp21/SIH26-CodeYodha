"""Polygon simplification for oversized raster-to-polygon extraction output. Owner: Dev 2."""

import json

from shapely.geometry import mapping, shape

MAX_VERTICES = 40
RETRY_TOLERANCES = [0.00006, 0.00012, 0.00024]


def _count_vertices(geom) -> int:
    if geom.geom_type == "Polygon":
        return len(geom.exterior.coords) + sum(len(ring.coords) for ring in geom.interiors)
    if geom.geom_type == "MultiPolygon":
        return sum(_count_vertices(part) for part in geom.geoms)
    raise ValueError(f"Unsupported geometry type: {geom.geom_type}")


def _simplify_valid(geom, tolerance: float, feature_id):
    """Simplify at tolerance; repair with buffer(0) if the result comes out invalid."""
    simplified = geom.simplify(tolerance, preserve_topology=True)
    if not simplified.is_valid:
        print(f"[simplify] feature {feature_id}: simplify(tolerance={tolerance}) produced an "
              f"invalid geometry, repairing with buffer(0)")
        simplified = simplified.buffer(0)
    return simplified


def simplify_parcels(input_path: str, output_path: str, tolerance: float = 0.00003) -> dict:
    with open(input_path, "r", encoding="utf-8") as f:
        collection = json.load(f)

    summary = {}
    escalated = []
    out_features = []

    for idx, feature in enumerate(collection["features"]):
        feature_id = feature.get("id", idx)
        original_geom = shape(feature["geometry"])
        before_count = _count_vertices(original_geom)

        simplified_geom = _simplify_valid(original_geom, tolerance, feature_id)
        tolerance_used = tolerance

        steps_tried = 0
        for retry_tolerance in RETRY_TOLERANCES:
            if _count_vertices(simplified_geom) <= MAX_VERTICES:
                break
            steps_tried += 1
            simplified_geom = _simplify_valid(original_geom, retry_tolerance, feature_id)
            tolerance_used = retry_tolerance

        after_count = _count_vertices(simplified_geom)
        if steps_tried > 0:
            escalated.append((feature_id, steps_tried, tolerance_used, after_count))

        summary[feature_id] = {
            "before_vertex_count": before_count,
            "after_vertex_count": after_count,
        }

        out_feature = {
            "type": "Feature",
            "properties": feature.get("properties", {}),
            "geometry": mapping(simplified_geom),
        }
        if "id" in feature:
            out_feature["id"] = feature["id"]
        out_features.append(out_feature)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": out_features}, f)

    if escalated:
        print("\nFeatures that needed extra simplification passes:")
        for feature_id, steps_tried, tol, count in escalated:
            status = "OK" if count <= MAX_VERTICES else "STILL OVER LIMIT"
            print(f"  feature {feature_id}: {steps_tried} retry step(s), "
                  f"final tolerance={tol}, final vertex count={count} ({status})")

    return summary


if __name__ == "__main__":
    INPUT_PATH = "data/raw/segmentation/parcels_only.geojson"
    OUTPUT_PATH = "data/raw/segmentation/parcels_simplified.geojson"

    result = simplify_parcels(INPUT_PATH, OUTPUT_PATH)

    print(f"\n{'feature':>10} {'before':>8} {'after':>8}")
    for feature_id, counts in result.items():
        print(f"{str(feature_id):>10} {counts['before_vertex_count']:>8} {counts['after_vertex_count']:>8}")

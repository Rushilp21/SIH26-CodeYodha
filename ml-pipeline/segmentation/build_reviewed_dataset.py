"""Build a train-only human-feedback augmentation without running model training.

The target AOI is never used for validation, threshold selection, or testing.
Independent CadastreVision validation/test records are preserved from the base
manifest, while verified boundaries and labelled false positives become small,
georeferenced training windows.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/jl_fs/bhumisetu")
PATCH_SIZE = 512


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-export", type=Path, required=True)
    parser.add_argument("--base-manifest", type=Path,
                        default=ROOT / "datasets/cadastrevision/finetune_v3/manifest.json")
    parser.add_argument("--imagery-manifest", type=Path,
                        default=ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "datasets/cadastrevision/reviewed_feedback_v1")
    parser.add_argument("--window-size", type=int, default=2048)
    parser.add_argument("--location-cell-metres", type=float, default=384.0)
    parser.add_argument("--require-ready", action="store_true")
    return parser.parse_args()


def validate_review_export(document: dict) -> dict:
    if document.get("schema_version") != "bhumisetu.review-labels.v1":
        raise ValueError("Unsupported review export; expected bhumisetu.review-labels.v1")
    if document.get("type") != "FeatureCollection" or not isinstance(document.get("features"), list):
        raise ValueError("Review export must be a GeoJSON FeatureCollection")
    ids = []
    for feature in document["features"]:
        properties = feature.get("properties", {})
        parcel_id = properties.get("parcel_id")
        role = properties.get("training_role")
        if not isinstance(parcel_id, str) or role not in ("positive_boundary", "hard_negative"):
            raise ValueError("Every reviewed feature needs parcel_id and a supported training_role")
        if role == "hard_negative" and properties.get("false_positive_class") not in (
            "building", "road", "canal", "other"
        ):
            raise ValueError(f"Hard-negative parcel {parcel_id} has no valid false-positive class")
        ids.append(parcel_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Review export contains duplicate parcel IDs")
    return document.get("summary", {})


def validate_base_manifest(manifest: dict) -> dict[str, int]:
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("Base dataset manifest has no records array")
    counts = Counter(record.get("split") for record in records)
    if counts["train"] < 1 or counts["validation"] < 1 or counts["test"] < 1:
        raise ValueError("Base manifest must contain independent train, validation, and test locations")
    legacy = manifest.get("target_aoi_used_for_training_or_selection")
    selection = manifest.get("target_aoi_used_for_parameter_selection", legacy)
    testing = manifest.get("target_aoi_used_for_test", legacy)
    if selection is not False or testing is not False:
        raise ValueError("Base validation/test records do not prove target-AOI exclusion")
    return {key: int(counts[key]) for key in ("train", "validation", "test")}


def imagery_records(manifest: dict) -> list[dict]:
    records = manifest.get("records")
    if isinstance(records, list):
        return records
    if manifest.get("image"):
        return [manifest]
    raise ValueError("Imagery manifest contains neither an image nor records")


def _write_geojson(frame, path: Path, properties: list[str]) -> None:
    """Write CRS84 GeoJSON, including valid empty layers."""
    from shapely.geometry import mapping

    if frame.empty:
        document = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [],
        }
    else:
        geographic = frame.to_crs("EPSG:4326")
        document = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [{
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": {name: getattr(row, name) for name in properties},
            } for row in geographic.itertuples()],
        }
    path.write_text(json.dumps(document, separators=(",", ":")))


def _crop_image(source, centre_x: float, centre_y: float, size: int, destination: Path):
    import rasterio
    from rasterio.windows import Window

    row, col = source.index(centre_x, centre_y)
    width, height = min(size, source.width), min(size, source.height)
    col_off = max(0, min(source.width - width, col - width // 2))
    row_off = max(0, min(source.height - height, row - height // 2))
    window = Window(col_off, row_off, width, height)
    profile = source.profile.copy()
    profile.update(
        driver="GTiff", width=width, height=height, count=3,
        transform=source.window_transform(window), compress="deflate",
        tiled=True, blockxsize=min(512, width), blockysize=min(512, height), BIGTIFF="IF_SAFER",
    )
    temporary = destination.with_name(f".{destination.name}.tmp")
    with rasterio.open(temporary, "w", **profile) as output:
        output.write(source.read([1, 2, 3], window=window))
        output.write_mask(source.dataset_mask(window=window))
    temporary.replace(destination)
    return window, tuple(rasterio.windows.bounds(window, source.transform))


def build(args: argparse.Namespace) -> dict:
    import geopandas as gpd
    import rasterio
    from shapely.geometry import box

    if args.window_size < PATCH_SIZE or args.window_size % PATCH_SIZE:
        raise ValueError(f"window-size must be a multiple of {PATCH_SIZE}")
    review = json.loads(args.review_export.read_text())
    review_summary = validate_review_export(review)
    if args.require_ready and not review_summary.get("training_ready", False):
        raise RuntimeError("Review export has not reached its positive/negative coverage minimums")
    base = json.loads(args.base_manifest.read_text())
    base_counts = validate_base_manifest(base)
    images = imagery_records(json.loads(args.imagery_manifest.read_text()))
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing reviewed dataset: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    reviewed = gpd.GeoDataFrame.from_features(review["features"], crs="EPSG:4326")
    reviewed["parcel_id"] = reviewed["parcel_id"].astype(str)
    assigned_ids: set[str] = set()
    feedback_records = []
    class_counts = Counter()
    role_counts = Counter()

    for image_index, image_record in enumerate(images):
        image_path = Path(image_record["image"])
        with rasterio.open(image_path) as source:
            if source.crs is None or source.transform.is_identity:
                raise RuntimeError(f"Review imagery is not georeferenced: {image_path}")
            projected = reviewed.to_crs(source.crs)
            projected = projected[~projected["parcel_id"].isin(assigned_ids)].copy()
            projected = projected[projected.intersects(box(*source.bounds))].copy()
            if projected.empty:
                continue
            groups = defaultdict(list)
            for index, row in projected.iterrows():
                centre = row.geometry.centroid
                key = (math.floor(centre.x / args.location_cell_metres), math.floor(centre.y / args.location_cell_metres))
                groups[key].append(index)
            for group_index, indices in enumerate(groups.values()):
                group = projected.loc[indices].copy()
                centre = group.geometry.unary_union.centroid
                name = f"reviewed_{image_index:02d}_{group_index:03d}"
                image_output = args.output_dir / f"{name}.tif"
                window, bounds = _crop_image(source, centre.x, centre.y, args.window_size, image_output)
                crop_box = box(*bounds)
                group = projected.loc[indices].copy()
                if group.empty:
                    continue
                group.geometry = group.geometry.intersection(crop_box)
                group = group[~group.geometry.is_empty & group.geometry.is_valid].copy()
                positives = group[group["training_role"] == "positive_boundary"].copy()
                negatives = group[group["training_role"] == "hard_negative"].copy()
                lines = positives.copy()
                if not lines.empty:
                    lines.geometry = lines.geometry.boundary
                negatives["feature_type"] = negatives["false_positive_class"] if "false_positive_class" in negatives else "other"

                faces_path = args.output_dir / f"{name}_reference_faces.geojson"
                lines_path = args.output_dir / f"{name}_reference_lines.geojson"
                negatives_path = args.output_dir / f"{name}_hard_negatives.geojson"
                _write_geojson(positives, faces_path, ["parcel_id"])
                _write_geojson(lines, lines_path, ["parcel_id"])
                _write_geojson(negatives, negatives_path, ["parcel_id", "feature_type"])

                used_ids = set(group["parcel_id"])
                assigned_ids.update(used_ids)
                role_counts.update(group["training_role"])
                class_counts.update(negatives["feature_type"] if not negatives.empty else [])
                feedback_records.append({
                    "name": name,
                    "split": "train",
                    "source": "human_review_feedback",
                    "image": str(image_output),
                    "reference": str(faces_path),
                    "reference_faces": str(faces_path),
                    "reference_lines": str(lines_path),
                    "hard_negative_features": str(negatives_path),
                    "hard_negative_counts": dict(Counter(negatives["feature_type"])) if not negatives.empty else {},
                    "crs": source.crs.to_string(),
                    "transform": list(source.window_transform(window))[:6],
                    "bounds": bounds,
                    "shape": [int(window.height), int(window.width)],
                    "reviewed_parcel_ids": sorted(used_ids),
                    "positive_boundary_count": int(len(positives)),
                    "hard_negative_count": int(len(negatives)),
                })

    unmatched = sorted(set(reviewed["parcel_id"]) - assigned_ids)
    combined = [*base["records"], *feedback_records]
    combined_manifest = {
        **{key: value for key, value in base.items() if key != "records"},
        "version": args.output_dir.name,
        "records": combined,
        "review_export": str(args.review_export),
        "review_imagery_manifest": str(args.imagery_manifest),
        "target_aoi_used_for_training": bool(feedback_records),
        "target_aoi_used_for_parameter_selection": False,
        "target_aoi_used_for_test": False,
        "target_aoi_used_for_training_or_selection": bool(feedback_records),
        "feedback_policy": "Human-reviewed target labels are train-only; independent CadastreVision validation and test locations remain unchanged.",
    }
    report = {
        "reviewed_features": int(len(reviewed)),
        "matched_reviewed_features": len(assigned_ids),
        "unmatched_reviewed_features": unmatched,
        "feedback_windows": len(feedback_records),
        "positive_boundaries": role_counts["positive_boundary"],
        "hard_negatives": role_counts["hard_negative"],
        "hard_negative_classes": dict(sorted(class_counts.items())),
        "base_split_counts": base_counts,
        "combined_split_counts": dict(Counter(record["split"] for record in combined)),
        "review_training_ready": bool(review_summary.get("training_ready", False)),
        "spatial_leakage_guard": "feedback records train-only; base validation/test unchanged",
        "dataset_ready": not unmatched and bool(feedback_records) and bool(review_summary.get("training_ready", False)),
    }
    if unmatched:
        report["blocking_issue"] = "Some reviewed geometries do not intersect the supplied georeferenced imagery."
    manifest_path = args.output_dir / "manifest.json"
    report_path = args.output_dir / "pretraining_report.json"
    manifest_path.write_text(json.dumps(combined_manifest, indent=2))
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    args = arguments()
    report = build(args)
    print("REVIEWED DATASET PREPARATION PASS", json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

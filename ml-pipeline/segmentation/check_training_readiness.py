"""Audit a CadastreVision manifest before spending GPU time.

This is deliberately read-only.  It verifies spatial split isolation,
georeferencing, thin boundary targets, and road/building/canal hard-negative
coverage.  Human-reviewed target-AOI feedback is reported separately because
OSM ancillary labels are useful hard negatives, but are not a substitute for
explicit reviewer decisions.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path("/home/jl_fs/bhumisetu")
REQUIRED_SPLITS = {"train": 9, "validation": 3, "test": 3}
REQUIRED_NEGATIVE_CLASSES = {"road", "building", "canal"}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=ROOT / "datasets/cadastrevision/finetune_v3/manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/training_readiness/report.json",
    )
    parser.add_argument("--require-human-feedback", action="store_true")
    return parser.parse_args()


def manifest_contract(manifest: dict) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return ["Manifest has no records."], warnings

    split_counts = Counter(record.get("split") for record in records)
    for split, minimum in REQUIRED_SPLITS.items():
        if split_counts[split] < minimum:
            blockers.append(f"{split} needs at least {minimum} windows; found {split_counts[split]}.")

    legacy = manifest.get("target_aoi_used_for_training_or_selection")
    if manifest.get("target_aoi_used_for_parameter_selection", legacy) is not False:
        blockers.append("Manifest does not prove target-AOI exclusion from parameter selection.")
    if manifest.get("target_aoi_used_for_test", legacy) is not False:
        blockers.append("Manifest does not prove target-AOI exclusion from testing.")

    feedback = [record for record in records if record.get("source") == "human_review_feedback"]
    if any(record.get("split") != "train" for record in feedback):
        blockers.append("Human-review feedback appears outside the training split.")
    if not feedback:
        warnings.append("No human-reviewed feedback windows are present; smoke testing may proceed on independent OSM negatives only.")
    return blockers, warnings


def reviewed_feedback_ready(manifest: dict) -> bool:
    """Require labels actually matched to imagery to pass the coverage gate."""
    summary = manifest.get("matched_review_summary", manifest.get("review_summary", {}))
    return bool(summary.get("training_ready", False))


def valid_boundary_coverage(record: dict, boundary_pixels: int, hard_negative_pixels: int) -> bool:
    """Allow explicitly reviewed negative-only windows, but not empty base records."""
    if boundary_pixels > 0:
        return True
    return (
        record.get("source") == "human_review_feedback"
        and int(record.get("hard_negative_count", 0)) > 0
        and hard_negative_pixels > 0
    )


def audit(manifest_path: Path, require_human_feedback: bool) -> dict:
    import rasterio
    from shapely.geometry import box

    from finetune_cadastrevision import IGNORE, training_masks

    manifest = json.loads(manifest_path.read_text())
    blockers, warnings = manifest_contract(manifest)
    records = manifest.get("records", [])
    record_reports = []
    split_boxes: list[tuple[str, str, object]] = []
    negative_features = Counter()
    negative_pixels = Counter()
    feedback_records = 0
    review_summary = manifest.get("matched_review_summary", manifest.get("review_summary", {}))
    human_feedback_ready = reviewed_feedback_ready(manifest)

    for record in records:
        name = str(record.get("name", "unnamed"))
        split = str(record.get("split", "missing"))
        missing = [
            key for key in ("image", "reference_lines", "reference_faces", "hard_negative_features")
            if not record.get(key) or not Path(record[key]).is_file()
        ]
        if missing:
            blockers.append(f"{name} is missing files for: {', '.join(missing)}.")
            continue
        try:
            with rasterio.open(record["image"]) as source:
                if source.crs is None or source.transform.is_identity:
                    blockers.append(f"{name} imagery is not georeferenced.")
                    continue
                bounds = tuple(source.bounds)
                split_boxes.append((name, split, box(*bounds)))
                if record.get("crs") and source.crs.to_string() != record["crs"]:
                    blockers.append(f"{name} CRS differs from its manifest contract.")
            _, boundary, hard_negative = training_masks(record)
        except Exception as error:
            blockers.append(f"{name} mask audit failed: {error}")
            continue

        valid = boundary != IGNORE
        boundary_pixels = int(((boundary == 1) & valid).sum())
        valid_pixels = int(valid.sum())
        boundary_ratio = boundary_pixels / max(valid_pixels, 1)
        total_hard_negative_pixels = int((hard_negative > 0).sum())
        if not valid_boundary_coverage(record, boundary_pixels, total_hard_negative_pixels):
            blockers.append(f"{name} has neither rasterized cadastral boundaries nor explicit hard-negative evidence.")
        if boundary_ratio > 0.15:
            blockers.append(f"{name} boundary mask is not thin ({boundary_ratio:.2%} of valid pixels).")
        overlap = int(((boundary == 1) & (hard_negative > 0)).sum())
        if overlap:
            blockers.append(f"{name} has {overlap} boundary/hard-negative conflict pixels after protection.")

        per_record_pixels = {}
        for type_id, class_name in ((1, "road"), (2, "building"), (3, "canal"), (4, "other")):
            count = int((hard_negative == type_id).sum())
            per_record_pixels[class_name] = count
            negative_pixels[class_name] += count
        negative_features.update(record.get("hard_negative_counts", {}))
        if record.get("source") == "human_review_feedback":
            feedback_records += 1
        record_reports.append({
            "name": name,
            "split": split,
            "boundary_pixels": boundary_pixels,
            "boundary_ratio": boundary_ratio,
            "negative_only_feedback_window": boundary_pixels == 0 and total_hard_negative_pixels > 0,
            "hard_negative_pixels": per_record_pixels,
        })

    for index, (left_name, left_split, left_box) in enumerate(split_boxes):
        for right_name, right_split, right_box in split_boxes[index + 1:]:
            if left_split != right_split and left_box.intersects(right_box):
                blockers.append(f"Spatial split leakage: {left_name} ({left_split}) intersects {right_name} ({right_split}).")

    absent = sorted(name for name in REQUIRED_NEGATIVE_CLASSES if negative_pixels[name] == 0)
    if absent:
        blockers.append(f"Rasterized hard-negative coverage is missing: {', '.join(absent)}.")
    if feedback_records and not human_feedback_ready:
        warnings.append("Human feedback windows exist, but their source export did not meet the review coverage minimums.")
    if require_human_feedback and not human_feedback_ready:
        blockers.append("Human-reviewed feedback was required but its export has not met the review coverage minimums.")

    split_counts = Counter(record.get("split") for record in records)
    report = {
        "schema_version": "bhumisetu.training-readiness.v1",
        "dataset_manifest": str(manifest_path),
        "ready_for_smoke_test": not blockers,
        "ready_for_heavy_training": not blockers and human_feedback_ready,
        "split_counts": {name: int(split_counts[name]) for name in REQUIRED_SPLITS},
        "spatial_split_isolated": not any(item.startswith("Spatial split leakage") for item in blockers),
        "hard_negative_feature_counts": dict(sorted(negative_features.items())),
        "hard_negative_pixel_counts": dict(sorted(negative_pixels.items())),
        "human_feedback_windows": feedback_records,
        "human_feedback_summary": review_summary,
        "blockers": blockers,
        "warnings": warnings,
        "records": record_reports,
    }
    return report


def main() -> None:
    args = arguments()
    report = audit(args.dataset_manifest, args.require_human_feedback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp.json")
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(args.output)
    print(json.dumps(report, indent=2), flush=True)
    if not report["ready_for_smoke_test"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

"""Compare a versioned candidate with a baseline using report-only references."""

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from comparison import compare_polygon_sets

ROOT = Path("/home/jl_fs/bhumisetu")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-version", default="vectorization_v2")
    parser.add_argument("--baseline-version")
    parser.add_argument("--validation-baseline-version")
    return parser.parse_args()


def polygons(path: Path, crs: str):
    return list(gpd.read_file(path).to_crs(crs).geometry)


def validation_score(report: dict) -> float:
    metrics = report["validation_metrics"]
    return float(metrics.get("mean_harmonic_iou", metrics["harmonic_mean_best_iou"]))


def main() -> None:
    args = arguments()
    manifest = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
    crs = manifest["crs"]
    references = list(gpd.read_file(manifest["reference_faces"]).to_crs(crs).geometry)
    old = compare_polygon_sets(polygons(ROOT / "geojson/parcels_topology_cleaned.geojson", crs), references)
    candidate_dir = ROOT / "results" / args.candidate_version
    candidate = compare_polygon_sets(polygons(candidate_dir / "parcels_vectorized.geojson", crs), references)
    report = {
        "crs_for_metrics": crs,
        "reference_source": "CadastreVision brk_reference closed faces in target AOI",
        "target_reference_used_for_parameter_selection": False,
        "validation_and_target_reference_used_for_parameter_selection": False,
        "old_cleaned_output": old,
        # Keep the established v2 key for validate_outputs.py and consumers.
        "new_enclosed_face_vectorization": candidate,
        "candidate": candidate,
        "harmonic_iou_delta_from_old": candidate["harmonic_mean_best_iou"] - old["harmonic_mean_best_iou"],
    }
    if args.baseline_version:
        baseline_dir = ROOT / "results" / args.baseline_version
        baseline = compare_polygon_sets(polygons(baseline_dir / "parcels_vectorized.geojson", crs), references)
        candidate_calibration = json.loads((candidate_dir / "calibration_report.json").read_text())
        validation_baseline_dir = ROOT / "results" / (args.validation_baseline_version or args.baseline_version)
        baseline_calibration = json.loads((validation_baseline_dir / "calibration_report.json").read_text())
        report["baseline_version"] = args.baseline_version
        report["validation_baseline_version"] = args.validation_baseline_version or args.baseline_version
        report["baseline"] = baseline
        report["validation_harmonic_iou_delta"] = validation_score(candidate_calibration) - validation_score(baseline_calibration)
        report["target_harmonic_iou_delta"] = candidate["harmonic_mean_best_iou"] - baseline["harmonic_mean_best_iou"]
        report["promoted"] = (
            report["validation_harmonic_iou_delta"] >= 0
            and report["target_harmonic_iou_delta"] > 0
            and candidate["invalid_candidates"] == 0
        )
    (candidate_dir / "reference_comparison.json").write_text(json.dumps(report, indent=2))
    print("REFERENCE COMPARISON", json.dumps(report, indent=2), flush=True)
    if args.baseline_version and not report["promoted"]:
        raise RuntimeError(f"{args.candidate_version} failed promotion; {args.baseline_version} remains canonical")


if __name__ == "__main__":
    main()

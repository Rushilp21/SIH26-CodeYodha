"""Evaluate one SegFormer checkpoint through the complete cadastral chain."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/jl_fs/bhumisetu")
REPO = ROOT / "repo"
sys.path.insert(0, str(HERE / "src"))
from model import load_segformer, model_sha256
from finetune_cadastrevision import metrics, select_threshold


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=REPO, check=True)


def overlap_pairs(frame: gpd.GeoDataFrame) -> int:
    geometries = list(frame.geometry)
    return sum(
        first.intersection(second).area > 0.01
        for index, first in enumerate(geometries)
        for second in geometries[index + 1:]
        if first.intersects(second)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-ppo", action="store_true")
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "results/chain_baseline_finetune_v3/report.json")
    args = parser.parse_args()
    result_dir = ROOT / "results" / f"chain_{args.version}"
    result_dir.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.dataset_manifest.read_text())
    splits = {
        split: [record for record in manifest["records"] if record["split"] == split]
        for split in ("train", "validation", "test")
    }
    model, _, _, device = load_segformer(args.model_dir)
    validation = select_threshold(model, splits["validation"], device)
    pixel = {
        "train": metrics(model, splits["train"], device, validation["threshold"]),
        "validation": validation,
        "test": metrics(model, splits["test"], device, validation["threshold"]),
    }

    probability_version = f"chain_{args.version}"
    vector_version = f"chain_{args.version}"
    run(
        "ml-pipeline/segmentation/infer_cadastrevision.py",
        "--version", args.version, "--model-dir", str(args.model_dir),
        "--output-version", probability_version, "--dataset-manifest", str(args.dataset_manifest),
        "--skip-pixel-gate",
    )
    probability_manifest = ROOT / "probability_maps" / probability_version / "manifest.json"
    run(
        "ml-pipeline/vectorization/generate_candidates.py", "--profile", "multiwindow",
        "--output-version", vector_version, "--probability-manifest", str(probability_manifest),
    )
    run("ml-pipeline/vectorization/compare_reference.py", "--candidate-version", vector_version)
    vector_dir = ROOT / "results" / vector_version
    candidates = gpd.read_file(vector_dir / "parcels_vectorized.geojson").to_crs("EPSG:28992")
    topology = {
        "candidate_count": len(candidates), "invalid_geometries": int((~candidates.geometry.is_valid).sum()),
        "overlap_pairs": overlap_pairs(candidates),
    }
    if args.run_ppo:
        run(
            "ml-pipeline/vectorization/refine_candidates.py", "--candidate-version", vector_version,
            "--probability-manifest", str(probability_manifest),
        )
    calibration = json.loads((vector_dir / "calibration_report.json").read_text())
    target = json.loads((vector_dir / "reference_comparison.json").read_text())
    ppo_report = json.loads((vector_dir / "rl_comparison.json").read_text()) if args.run_ppo else None
    report = {
        "version": args.version, "model": str(args.model_dir), "model_sha256": model_sha256(args.model_dir),
        "dataset_manifest": str(args.dataset_manifest), "pixel_metrics": pixel,
        "polygon_training": calibration["training_summary"],
        "polygon_validation": calibration["validation_metrics"],
        "polygon_target_report_only": target["candidate"], "topology_before_ppo": topology,
        "ppo": ppo_report,
        "target_aoi_used_for_model_or_parameter_selection": False,
    }
    if args.baseline_report.is_file() and args.baseline_report.resolve() != (result_dir / "report.json").resolve():
        baseline = json.loads(args.baseline_report.read_text())
        deltas = {
            "validation_pixel_iou": pixel["validation"]["boundary_iou"] - baseline["pixel_metrics"]["validation"]["boundary_iou"],
            "test_pixel_iou": pixel["test"]["boundary_iou"] - baseline["pixel_metrics"]["test"]["boundary_iou"],
            "test_false_positive_rate": pixel["test"]["false_positive_rate"] - baseline["pixel_metrics"]["test"]["false_positive_rate"],
            "validation_polygon_iou": calibration["validation_metrics"]["harmonic_mean_best_iou"] - baseline["polygon_validation"]["harmonic_mean_best_iou"],
            "target_post_ppo_iou": (
                ppo_report["reference_metrics_after_rl"]["harmonic_mean_best_iou"]
                - baseline["ppo"]["reference_metrics_after_rl"]["harmonic_mean_best_iou"]
            ) if ppo_report and baseline.get("ppo") else None,
        }
        selection_eligible = (
            deltas["validation_pixel_iou"] > 0 and deltas["validation_polygon_iou"] > 0
            and topology["invalid_geometries"] == 0 and topology["overlap_pairs"] == 0
        )
        report["baseline_comparison"] = {
            "baseline_report": str(args.baseline_report), "deltas": deltas,
            "selection_eligible_without_target": selection_eligible,
            "final_promotion_eligible": bool(
                selection_eligible and deltas["test_pixel_iou"] > 0
                and deltas["test_false_positive_rate"] < 0
                and deltas["target_post_ppo_iou"] is not None and deltas["target_post_ppo_iou"] > 0
            ),
        }
    temporary = result_dir / ".report.tmp.json"
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(result_dir / "report.json")
    print("MODEL CHAIN PASS", json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

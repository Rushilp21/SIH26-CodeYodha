"""Final immutable gate: pixel quality and post-PPO parcel accuracy must improve."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from comparison import compare_polygon_sets

ROOT = Path("/home/jl_fs/bhumisetu")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument("--baseline-version", default="vectorization_v2")
    parser.add_argument("--finetune-version", required=True)
    args = parser.parse_args()
    candidate_dir = ROOT / "results" / args.candidate_version
    baseline_dir = ROOT / "results" / args.baseline_version
    pixel = json.loads((ROOT / "results" / f"segformer_{args.finetune_version}" / "training_report.json").read_text())
    vector = json.loads((candidate_dir / "reference_comparison.json").read_text())
    candidate_rl = json.loads((candidate_dir / "rl_comparison.json").read_text())
    baseline_rl = json.loads((baseline_dir / "rl_comparison.json").read_text())
    manifest = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
    crs = manifest["crs"]
    references = list(gpd.read_file(manifest["reference_faces"]).to_crs(crs).geometry)
    candidate_geometries = list(gpd.read_file(candidate_dir / "parcels_vectorized_rl_refined.geojson").to_crs(crs).geometry)
    baseline_geometries = list(gpd.read_file(baseline_dir / "parcels_vectorized_rl_refined.geojson").to_crs(crs).geometry)
    candidate_final = compare_polygon_sets(candidate_geometries, references)
    baseline_final = compare_polygon_sets(baseline_geometries, references)
    final_delta = candidate_final["harmonic_mean_best_iou"] - baseline_final["harmonic_mean_best_iou"]
    promoted = (
        pixel.get("pixel_promotion_gate_passed") is True
        and vector.get("promoted") is True
        and final_delta > 0
        and candidate_final["invalid_candidates"] == 0
        and candidate_rl["overlap_pairs_after"] <= candidate_rl["overlap_pairs_before"]
        and candidate_rl["alignment_after"] >= candidate_rl["alignment_before"]
    )
    report = {
        "candidate_version": args.candidate_version, "baseline_version": args.baseline_version,
        "finetune_version": args.finetune_version, "pixel_gate_passed": pixel.get("pixel_promotion_gate_passed"),
        "pre_rl_vectorization_gate_passed": vector.get("promoted"),
        "baseline_final_parcel_metrics": baseline_final, "candidate_final_parcel_metrics": candidate_final,
        "final_harmonic_iou_delta": final_delta,
        "candidate_topology": {"invalid_after": candidate_rl["invalid_after"],
                               "overlap_pairs_before": candidate_rl["overlap_pairs_before"],
                               "overlap_pairs_after": candidate_rl["overlap_pairs_after"]},
        "promoted": promoted,
        "promotion_policy": "pixel validation+test, held-out vectorization, target vectorization, and post-PPO target accuracy must all pass",
    }
    temporary = candidate_dir / ".promotion_report.tmp.json"
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(candidate_dir / "promotion_report.json")
    print("FINAL PROMOTION", json.dumps(report, indent=2), flush=True)
    if not promoted:
        raise RuntimeError(f"{args.candidate_version} failed final promotion; {args.baseline_version} remains canonical")


if __name__ == "__main__":
    main()

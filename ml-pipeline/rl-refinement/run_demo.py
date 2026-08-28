"""Dev 2 end-to-end demo: train PPO per parcel, refine all 15 parcels, and
report the before/after overlap-violation reduction via validate_topology().

Run from repo root:
    .venv/Scripts/python.exe ml-pipeline/rl-refinement/run_demo.py
"""

from __future__ import annotations

import json
import sys
import uuid
from collections import Counter
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

REPO_ROOT = Path(__file__).resolve().parents[2]
RL_SRC = Path(__file__).resolve().parent / "src"
VECTORIZATION_SRC = REPO_ROOT / "ml-pipeline" / "vectorization" / "src"
sys.path.insert(0, str(RL_SRC))
sys.path.insert(0, str(VECTORIZATION_SRC))

from agent import train_on_parcels  # noqa: E402
from inference import refine_parcel  # noqa: E402
from topology import PROCESSING_CRS, STORAGE_CRS, validate_topology  # noqa: E402

PARCELS_PATH = REPO_ROOT / "data" / "raw" / "segmentation" / "parcels_simplified.geojson"
EXPERIMENTS_DIR = Path(__file__).resolve().parent / "experiments"

# Modest, "thousands not millions" per-parcel budget. Calibrated against a
# greedy-oracle feasibility check (see PR discussion): even a step-optimal
# policy over 300 steps @ 2m only cuts one heavily-overlapped parcel's
# topology penalty by ~22%, so these overlaps (segmentation bleed, thousands
# of sq m on ~400m parcels) are not fully closeable via small vertex nudges
# within a hackathon-night training budget. This run reports the real,
# partial reduction rather than forcing violations to zero.
TIMESTEPS_PER_PARCEL = 800
MAX_STEPS = 120
STEP_M = 1.5

_TO_PROCESSING = Transformer.from_crs(STORAGE_CRS, PROCESSING_CRS, always_xy=True)


def _project_exterior(geometry: dict) -> np.ndarray:
    coords = geometry["coordinates"][0]
    xs, ys = _TO_PROCESSING.transform([c[0] for c in coords], [c[1] for c in coords])
    return np.column_stack([xs, ys]).astype(np.float32)


def _violation_counts(report: dict) -> Counter:
    return Counter(v["type"] for v in report["violations"])


def _total_overlap_area_sqm(features: list) -> float:
    """Sum of pairwise overlap area (each pair counted once), in PROCESSING_CRS."""
    transformer = Transformer.from_crs(STORAGE_CRS, PROCESSING_CRS, always_xy=True)
    geoms = [shapely_transform(transformer.transform, shape(f["geometry"])) for f in features]
    total = 0.0
    for i in range(len(geoms)):
        if not geoms[i].is_valid:
            continue
        for j in range(i + 1, len(geoms)):
            if not geoms[j].is_valid or not geoms[i].intersects(geoms[j]):
                continue
            total += geoms[i].intersection(geoms[j]).area
    return total


def main() -> None:
    with open(PARCELS_PATH, "r", encoding="utf-8") as f:
        collection = json.load(f)
    features = collection["features"]
    n = len(features)
    print(f"Loaded {n} parcels from {PARCELS_PATH.relative_to(REPO_ROOT)}")

    print("\n=== BEFORE refinement ===")
    before_report = validate_topology(features)
    before_counts = _violation_counts(before_report)
    print(f"valid: {before_report['valid']}  total violations: {len(before_report['violations'])}")
    print(f"  by type: {dict(before_counts)}")

    parcels_xy = [_project_exterior(f["geometry"]) for f in features]

    print(f"\n=== TRAINING (PPO, {TIMESTEPS_PER_PARCEL} timesteps/parcel, {n} parcels) ===")
    train_results = train_on_parcels(
        parcels_xy,
        timesteps_per_parcel=TIMESTEPS_PER_PARCEL,
        max_steps=MAX_STEPS,
        step_m=STEP_M,
    )
    for r in train_results:
        print(f"  parcel {r['parcel_index']:2d}  n_vertices={r['n_vertices']:2d}  model={r['model_path']}")

    print("\n=== INFERENCE (refine all parcels) ===")
    refined_features = []
    breakdown_rows = []
    for idx, feat in enumerate(features):
        neighbor_geometries = [f["geometry"] for j, f in enumerate(features) if j != idx]
        source_tile_id = feat["properties"].get("source_tile_id", str(idx))
        payload = {
            "parcel_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"bhumisetu:parcel:{idx}:{source_tile_id}")),
            "geometry": feat["geometry"],
            "neighbor_geometries": neighbor_geometries,
            "model_path": train_results[idx]["model_path"],
            "segmentation_score": feat["properties"].get("raw_confidence", 0.0),
            "max_steps": MAX_STEPS,
            "step_m": STEP_M,
        }
        result = refine_parcel(payload)
        refined_features.append(
            {"type": "Feature", "properties": feat["properties"], "geometry": result["geometry"]}
        )
        breakdown_rows.append((idx, result))

    print("\n=== AFTER refinement ===")
    after_report = validate_topology(refined_features)
    after_counts = _violation_counts(after_report)
    print(f"valid: {after_report['valid']}  total violations: {len(after_report['violations'])}")
    print(f"  by type: {dict(after_counts)}")

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPERIMENTS_DIR / "refined_parcels.geojson"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": refined_features}, f)
    print(f"\nSaved refined geometries to {out_path.relative_to(REPO_ROOT)}")

    before_area = _total_overlap_area_sqm(features)
    after_area = _total_overlap_area_sqm(refined_features)
    pct_change = (after_area - before_area) / before_area * 100 if before_area else 0.0

    print("\n=== SUMMARY ===")
    print(f"{'metric':<24}{'before':>14}{'after':>14}")
    print(f"{'total violations':<24}{len(before_report['violations']):>14}{len(after_report['violations']):>14}")
    for vtype in sorted(set(before_counts) | set(after_counts)):
        print(f"{'  ' + vtype:<24}{before_counts.get(vtype, 0):>14}{after_counts.get(vtype, 0):>14}")
    print(f"{'total overlap area (sqm)':<24}{before_area:>14.1f}{after_area:>14.1f}  ({pct_change:+.1f}%)")

    print("\n=== PER-PARCEL REWARD BREAKDOWN ===")
    header = f"{'idx':>3} {'confidence':>10} {'topology':>9} {'regularity':>10} {'deviation':>9} {'seg':>6}"
    print(header)
    for idx, result in breakdown_rows:
        print(
            f"{idx:>3} {result['confidence_score']:>10.3f} {result['topology_score']:>9.3f} "
            f"{result['regularity_score']:>10.3f} {result['deviation_from_baseline_score']:>9.3f} "
            f"{result['segmentation_score']:>6.3f}"
        )


if __name__ == "__main__":
    main()

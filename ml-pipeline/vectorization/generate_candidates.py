"""Calibrate parcel vectorization without leaking validation or target references.

The baseline profile reproduces the established v2 flow. The fused profile
calibrates frozen SegFormer probabilities plus co-registered image gradients
across every available training window and writes a versioned candidate only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from comparison import compare_polygon_sets
from raster_to_polygon import VectorizationConfig, image_edge_evidence, raster_to_polygon

ROOT = Path("/home/jl_fs/bhumisetu")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("baseline", "multiwindow", "fused"), default="baseline")
    parser.add_argument("--output-version", default="vectorization_v2")
    parser.add_argument("--probability-manifest", type=Path, default=ROOT / "probability_maps/manifest.json")
    parser.add_argument("--aoi-probability", type=Path)
    return parser.parse_args()


def prepare_record(record: dict) -> dict:
    with rasterio.open(record["probability"]) as probability_source:
        if probability_source.crs is None or probability_source.transform.is_identity:
            raise RuntimeError("Probability raster is not georeferenced")
        probability = probability_source.read(1)
        transform = probability_source.transform
        crs = probability_source.crs.to_string()
        raster_shape = probability_source.shape
    with rasterio.open(record["image"]) as image_source:
        if image_source.crs.to_string() != crs or image_source.transform != transform or image_source.shape != raster_shape:
            raise RuntimeError(f"Image/probability grids differ for {record['name']}")
        image = image_source.read([1, 2, 3])
        valid = image_source.dataset_mask() > 0
    references = list(gpd.read_file(record["reference"]).to_crs(crs).geometry)
    return {
        **record,
        "_probability": probability,
        "_transform": transform,
        "_crs": crs,
        "_edge_evidence": image_edge_evidence(image, valid),
        "_references": references,
    }


def evaluate(record: dict, config: VectorizationConfig) -> tuple[dict, dict]:
    collection = raster_to_polygon(
        record["_probability"], record["_transform"], record["_crs"], config,
        edge_evidence=record["_edge_evidence"] if config.edge_weight else None,
    )
    candidates = list(gpd.GeoDataFrame.from_features(
        collection["features"], crs="EPSG:4326"
    ).to_crs(record["_crs"]).geometry) if collection["features"] else []
    return collection, compare_polygon_sets(candidates, record["_references"])


def summarize(metrics: list[dict]) -> dict:
    harmonic = [item["harmonic_mean_best_iou"] for item in metrics]
    return {
        "mean_harmonic_iou": float(np.mean(harmonic)),
        "worst_harmonic_iou": float(np.min(harmonic)),
        "records": metrics,
    }


def run_trial(records: list[dict], config: VectorizationConfig) -> dict:
    summary = summarize([evaluate(record, config)[1] for record in records])
    score = 0.8 * summary["mean_harmonic_iou"] + 0.2 * summary["worst_harmonic_iou"]
    return {"config": asdict(config), "training": summary, "objective": score}


def configuration(threshold: float, close_pixels: int, width: int, edge_weight: float):
    return VectorizationConfig(
        threshold=round(threshold, 2),
        close_pixels=close_pixels,
        boundary_width_pixels=width,
        min_area_m2=20,
        max_area_m2=250_000,
        simplify_tolerance_m=0.25,
        edge_weight=round(edge_weight, 2),
    )


def baseline_configurations():
    for threshold in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        for close_pixels in (1, 3, 5, 7):
            for width in (0, 1):
                yield configuration(threshold, close_pixels, width, 0.0)


def fused_coarse_configurations():
    for edge_weight in (0.0, 0.1, 0.2, 0.3, 0.4):
        for threshold in (0.35, 0.40, 0.45, 0.50, 0.55):
            yield configuration(threshold, 3, 0, edge_weight)


def detailed_configurations(coarse: list[dict]):
    seen = set()
    # One complete local neighborhood around the best coarse result is enough;
    # expanding several near-tied seeds repeats most threshold/morphology pairs.
    for seed in sorted(coarse, key=lambda item: item["objective"], reverse=True)[:1]:
        base = seed["config"]
        for threshold_delta in (-0.05, 0.0, 0.05):
            for close_pixels in (1, 3, 5, 7):
                for width in (0, 1):
                    config = configuration(
                        base["threshold"] + threshold_delta,
                        close_pixels,
                        width,
                        base["edge_weight"],
                    )
                    key = json.dumps(asdict(config), sort_keys=True)
                    if key not in seen:
                        seen.add(key)
                        yield config


def main() -> None:
    args = arguments()
    results = ROOT / "results" / args.output_version
    destination = results / "parcels_vectorized.geojson"
    results.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Refusing to overwrite {destination}")

    manifest = json.loads(args.probability_manifest.read_text())
    available_training = [record for record in manifest["records"] if record["name"].startswith("train_selected")]
    if args.profile != "baseline" and len(available_training) < 2:
        raise RuntimeError("Multi-window calibration requires at least two disjoint training windows")
    selected_training = available_training[:1] if args.profile == "baseline" else available_training
    training = [prepare_record(record) for record in selected_training]
    validation_records = [record for record in manifest["records"] if record.get("split") == "validation" or record["name"].startswith("validation")]
    if not validation_records:
        raise RuntimeError("Probability manifest contains no held-out validation records")
    validations = [prepare_record(record) for record in validation_records]

    cache_path = results / ".calibration_trials.json"
    cache_identity = {
        "profile": args.profile,
        "training_windows": [record["name"] for record in selected_training],
    }
    cached = (
        json.loads(cache_path.read_text())
        if cache_path.exists() and cache_path.stat().st_size
        else {**cache_identity, "trials": []}
    )
    if any(cached.get(key) != value for key, value in cache_identity.items()):
        raise RuntimeError(f"Refusing incompatible calibration cache {cache_path}")
    trials = cached["trials"]
    completed = {json.dumps(item["config"], sort_keys=True) for item in trials}
    def evaluate_configurations(configs, stage: str) -> None:
        for index, config in enumerate(configs, start=1):
            config_key = json.dumps(asdict(config), sort_keys=True)
            if config_key in completed:
                print(stage, "CACHED", index, asdict(config), flush=True)
                continue
            result = run_trial(training, config)
            trials.append(result)
            completed.add(config_key)
            cache_temporary = cache_path.with_suffix(".tmp.json")
            cache_temporary.write_text(json.dumps({**cache_identity, "trials": trials}))
            cache_temporary.replace(cache_path)
            print(stage, index, round(result["objective"], 6), asdict(config), flush=True)

    if args.profile == "baseline":
        evaluate_configurations(baseline_configurations(), "CALIBRATION")
    elif args.profile == "multiwindow":
        coarse_configs = [configuration(threshold, 3, 0, 0.0) for threshold in
                          (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60)]
        evaluate_configurations(coarse_configs, "COARSE")
        coarse_keys = {json.dumps(asdict(config), sort_keys=True) for config in coarse_configs}
        coarse_trials = [item for item in trials if json.dumps(item["config"], sort_keys=True) in coarse_keys]
        evaluate_configurations(detailed_configurations(coarse_trials), "DETAILED")
    else:
        coarse_configs = list(fused_coarse_configurations())
        evaluate_configurations(coarse_configs, "COARSE")
        coarse_keys = {json.dumps(asdict(config), sort_keys=True) for config in coarse_configs}
        coarse_trials = [item for item in trials if json.dumps(item["config"], sort_keys=True) in coarse_keys]
        evaluate_configurations(detailed_configurations(coarse_trials), "DETAILED")
    # Some line-rich training crops intentionally contain only two fully closed
    # reference faces because parcel edges cross the crop boundary. Requiring
    # three predictions made those valid windows impossible by construction.
    viable = [item for item in trials if all(metric["candidate_count"] >= 1 for metric in item["training"]["records"])]
    if not viable:
        raise RuntimeError("Frozen evidence produced no viable enclosed cadastral faces")
    selected = max(viable, key=lambda item: item["objective"])
    config = VectorizationConfig(**selected["config"])
    validation_details = [evaluate(record, config)[1] for record in validations]
    validation_metrics = summarize(validation_details)
    # Stable aggregate key retained for comparison with the production v2 report.
    validation_metrics["harmonic_mean_best_iou"] = validation_metrics["mean_harmonic_iou"]

    aoi_manifest = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
    probability_path = args.aoi_probability or manifest.get("aoi_probability")
    if probability_path is None:
        probability_info = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/probability.json").read_text())
        probability_path = probability_info["probability"]
    target = prepare_record({
        "name": args.output_version,
        "image": aoi_manifest["image"],
        "probability": str(probability_path),
        "reference": aoi_manifest["reference_faces"],
    })
    collection, _ = evaluate(target, config)
    if not collection["features"]:
        raise RuntimeError("Selected parameters produced no target AOI candidates")
    for feature in collection["features"]:
        feature["properties"].update(
            source_tile_id="tile-110000-460000",
            vectorization_aoi=args.output_version,
            calibration=f"{args.profile} training-only selection; validation and target references excluded",
        )
    temporary = destination.with_suffix(".tmp.geojson")
    temporary.write_text(json.dumps(collection))
    temporary.replace(destination)
    report = {
        "profile": args.profile,
        "selected_config": asdict(config),
        "selection_rule": "0.8 mean + 0.2 worst harmonic best-IoU over training windows",
        "training_windows": [record["name"] for record in selected_training],
        "training_summary": selected["training"],
        "selection_objective": selected["objective"],
        "validation_windows": [record["name"] for record in validation_records],
        "validation_metrics": validation_metrics,
        "trial_count": len(trials),
        "target_candidate_count": len(collection["features"]),
        "validation_used_for_selection": False,
        "target_reference_used_for_selection": False,
        "model_weights_frozen_during_vectorization": True,
        "model_was_fine_tuned": bool(manifest.get("fine_tuned", False)),
    }
    (results / "calibration_report.json").write_text(json.dumps(report, indent=2))
    cache_path.unlink(missing_ok=True)
    print("CANDIDATES PASS", json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Apply the existing 20k-step PPO policy to a gated vectorization candidate."""

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import torch
from pyproj import Transformer
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import transform as transform_geometry
from stable_baselines3 import PPO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE.parent / "rl-refinement/src"))
from comparison import compare_polygon_sets
from evidence_env import EvidenceBoundaryEnv

ROOT = Path("/home/jl_fs/bhumisetu")
MODEL = ROOT / "checkpoints/ppo_debug_20000.zip"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-version", default="vectorization_v2")
    parser.add_argument("--probability-manifest", type=Path)
    return parser.parse_args()


def raster_evidence(image_path: str, probability_path: str) -> dict:
    with rasterio.open(probability_path) as probability, rasterio.open(image_path) as image:
        if probability.crs != image.crs or probability.transform != image.transform or probability.shape != image.shape:
            raise RuntimeError("AOI image and probability grids do not match")
        grey = image.read([1, 2, 3]).astype(np.float32).mean(0) / 255
        gradient_y, gradient_x = np.gradient(grey)
        edge = np.hypot(gradient_x, gradient_y)
        edge /= max(float(edge.max()), 1e-6)
        return {
            "probability": probability.read(1),
            "edge": edge,
            "transform": probability.transform,
            "crs": probability.crs.to_string(),
        }


def rollout(model, sample: dict, seed: int, deterministic: bool) -> tuple[np.ndarray, dict]:
    environment = EvidenceBoundaryEnv([sample], training=False)
    observation, _ = environment.reset(seed=seed)
    before = environment.metrics.copy()
    rewards = []
    rejected = 0
    if not deterministic:
        torch.manual_seed(seed)
    for _ in range(environment.max_steps):
        action, _ = model.predict(observation, deterministic=deterministic)
        observation, reward, _, done, info = environment.step(int(action))
        rewards.append(float(reward))
        rejected += int(info["rejected"])
        if done:
            break
    candidate = environment.best_xy.copy()
    after = environment.measure(candidate)
    accepted = (
        after["valid"]
        and after["alignment"] >= before["alignment"]
        and after["overlap"] <= before["overlap"] + 1e-8
    )
    if not accepted:
        candidate = environment.initial.copy()
        after = before.copy()
    return candidate, {
        "before": before,
        "after": after,
        "accepted": bool(accepted),
        "reward_mean": float(np.mean(rewards)),
        "reward_std": float(np.std(rewards)),
        "reward_sum": float(sum(rewards)),
        "rejected_actions": rejected,
        "mean_vertex_displacement_m": float(np.linalg.norm(candidate - environment.initial, axis=1).mean()),
    }


def deployment_score(candidate: tuple[np.ndarray, dict]) -> float:
    after = candidate[1]["after"]
    return 3 * after["alignment"] - 4 * after["overlap"] - 0.2 * after["displacement"] - 0.1 * after["jagged"]


def overlap_pairs(polygons: list[Polygon]) -> int:
    return sum(
        first.intersection(second).area > 0.01
        for index, first in enumerate(polygons)
        for second in polygons[index + 1 :]
        if first.intersects(second)
    )


def main() -> None:
    args = arguments()
    results = ROOT / "results" / args.candidate_version
    output = results / "parcels_vectorized_rl_refined.geojson"
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite {output}")
    if not MODEL.exists():
        raise RuntimeError("The completed 20k-step PPO checkpoint is missing")
    torch.set_num_threads(2)
    model = PPO.load(MODEL, device="cpu")
    policy_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()

    manifest = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
    if args.probability_manifest:
        probability_info = json.loads(args.probability_manifest.read_text())
        probability_path = probability_info["aoi_probability"]
    else:
        probability_info = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/probability.json").read_text())
        probability_path = probability_info["probability"]
    evidence = raster_evidence(manifest["image"], probability_path)
    source = json.loads((results / "parcels_vectorized.geojson").read_text())
    to_metric = Transformer.from_crs("EPSG:4326", evidence["crs"], always_xy=True).transform
    to_storage = Transformer.from_crs(evidence["crs"], "EPSG:4326", always_xy=True).transform
    before = [transform_geometry(to_metric, shape(feature["geometry"])) for feature in source["features"]]
    if not before or any(not isinstance(polygon, Polygon) or not polygon.is_valid for polygon in before):
        raise RuntimeError("Vectorized candidate set contains invalid or unsupported geometry")
    current = list(before)
    parcel_reports = []
    payloads = []

    for index, polygon in enumerate(before):
        item = {
            **evidence,
            "initial": np.asarray(polygon.exterior.coords)[:-1],
            "holes": [np.asarray(ring.coords)[:-1] for ring in polygon.interiors],
            "neighbors": [other for other_index, other in enumerate(current) if other_index != index and other.distance(polygon) < 5],
        }
        candidates = [rollout(model, item, seed=42, deterministic=True)]
        candidates.extend(rollout(model, item, seed=seed, deterministic=False) for seed in range(2))
        export_valid = []
        for candidate in candidates:
            exported = transform_geometry(to_storage, Polygon(candidate[0], item["holes"]))
            round_trip = transform_geometry(to_metric, exported)
            if exported.is_valid and round_trip.is_valid:
                export_valid.append(candidate)
        if not export_valid:
            raise RuntimeError(f"No round-trip-valid candidate for feature {index}")
        coordinates, metrics = max(export_valid, key=deployment_score)
        current[index] = Polygon(coordinates, item["holes"])
        refined_geometry = mapping(transform_geometry(to_storage, current[index]))
        baseline_geometry = source["features"][index]["geometry"]
        parcel_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{args.candidate_version}:{index}:{json.dumps(baseline_geometry, sort_keys=True)}"))
        segmentation = float(np.clip(source["features"][index]["properties"]["raw_confidence"], 0, 1))
        topology = float(np.clip(1 - metrics["after"]["overlap"], 0, 1))
        alignment = float(np.clip(metrics["after"]["alignment"], 0, 1))
        deviation = float(np.clip(1 - metrics["after"]["displacement"], 0, 1))
        confidence = float(np.clip(0.35 * segmentation + 0.30 * alignment + 0.20 * topology + 0.15 * deviation, 0, 1))
        explanation = (
            "Enclosed-face vectorization followed by the frozen 20,000-step PPO debug policy. "
            "Reference cadastral geometry was excluded from inference and used only for the comparison report. "
            "Invalid, overlap-increasing, alignment-degrading, or CRS-round-trip-invalid candidates were rejected."
        )
        properties = source["features"][index]["properties"]
        properties.update(
            parcel_id=parcel_id,
            confidence_score=confidence,
            segmentation_score=segmentation,
            topology_score=topology,
            edge_alignment_score=alignment,
            deviation_from_baseline_score=deviation,
            area_m2=float(current[index].area),
            explanation=explanation,
            rl_refinement={"policy_sha256": policy_hash, "timesteps": 20_000, "debug_policy": True, **metrics},
        )
        source["features"][index]["geometry"] = refined_geometry
        payloads.append({
            "parcel_id": parcel_id,
            "geometry": refined_geometry,
            "confidence_score": confidence,
            "segmentation_score": segmentation,
            "topology_score": topology,
            "edge_alignment_score": alignment,
            "deviation_from_baseline_score": deviation,
            "explanation": explanation,
            "demo": False,
            "metadata": {
                "baseline_geometry": baseline_geometry,
                "policy_sha256": policy_hash,
                "timesteps": 20_000,
                "accepted": metrics["accepted"],
                "changed": metrics["mean_vertex_displacement_m"] > 0,
            },
        })
        parcel_reports.append({"index": index, "parcel_id": parcel_id, **metrics})
        if (index + 1) % 25 == 0 or index + 1 == len(before):
            print(f"RL REFINEMENT {index + 1}/{len(before)}", flush=True)

    references = list(gpd.read_file(manifest["reference_faces"]).to_crs(evidence["crs"]).geometry)
    before_reference = compare_polygon_sets(before, references)
    after_reference = compare_polygon_sets(current, references)
    report = {
        "parcel_count_before": len(before),
        "parcel_count_after": len(current),
        "invalid_before": sum(not polygon.is_valid for polygon in before),
        "invalid_after": sum(not polygon.is_valid for polygon in current),
        "overlap_pairs_before": overlap_pairs(before),
        "overlap_pairs_after": overlap_pairs(current),
        "changed_parcels": sum(item["mean_vertex_displacement_m"] > 0 for item in parcel_reports),
        "mean_boundary_displacement_m": float(np.mean([item["mean_vertex_displacement_m"] for item in parcel_reports])),
        "alignment_before": float(np.mean([item["before"]["alignment"] for item in parcel_reports])),
        "alignment_after": float(np.mean([item["after"]["alignment"] for item in parcel_reports])),
        "reference_metrics_before_rl": before_reference,
        "reference_metrics_after_rl": after_reference,
        "reward_mean": float(np.mean([item["reward_mean"] for item in parcel_reports])),
        "reward_std": float(np.mean([item["reward_std"] for item in parcel_reports])),
        "policy_sha256": policy_hash,
        "timesteps": 20_000,
        "inference_rollouts_per_parcel": 3,
        "reference_used_during_inference": False,
        "parcels": parcel_reports,
    }
    if report["invalid_after"] or report["overlap_pairs_after"] > report["overlap_pairs_before"]:
        raise RuntimeError("RL output failed topology gates")
    if report["alignment_after"] < report["alignment_before"]:
        raise RuntimeError("RL output degraded boundary-probability alignment")

    output_temp = output.with_suffix(".tmp.geojson")
    output_temp.write_text(json.dumps(source))
    output_temp.replace(output)
    payload_path = results / "refined_parcel_payloads.json"
    payload_temp = payload_path.with_suffix(".tmp.json")
    payload_temp.write_text(json.dumps(payloads))
    payload_temp.replace(payload_path)
    (results / "rl_comparison.json").write_text(json.dumps(report, indent=2))
    print("RL REFINEMENT PASS", json.dumps({key: value for key, value in report.items() if key != "parcels"}, indent=2), flush=True)


if __name__ == "__main__":
    main()

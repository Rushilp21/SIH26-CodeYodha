"""Fail-fast validation for the generated vectorization_v2 artifacts."""

import hashlib
import json
import uuid
from pathlib import Path

import geopandas as gpd
import rasterio
from shapely.geometry import shape

ROOT = Path("/home/jl_fs/bhumisetu")
AOI = ROOT / "datasets/cadastrevision/vectorization_v2"
RESULTS = ROOT / "results/vectorization_v2"


def main() -> None:
    manifest = json.loads((AOI / "manifest.json").read_text())
    probability = json.loads((AOI / "probability.json").read_text())
    candidates = json.loads((RESULTS / "parcels_vectorized.geojson").read_text())
    refined = json.loads((RESULTS / "parcels_vectorized_rl_refined.geojson").read_text())
    payloads = json.loads((RESULTS / "refined_parcel_payloads.json").read_text())
    reference = json.loads((RESULTS / "reference_comparison.json").read_text())
    rl = json.loads((RESULTS / "rl_comparison.json").read_text())

    count = len(candidates["features"])
    assert count == len(refined["features"]) == len(payloads) > 0
    ids = []
    scores = (
        "confidence_score",
        "segmentation_score",
        "topology_score",
        "edge_alignment_score",
        "deviation_from_baseline_score",
    )
    for feature, payload in zip(refined["features"], payloads):
        parcel_id = payload["parcel_id"]
        uuid.UUID(parcel_id)
        assert feature["properties"]["parcel_id"] == parcel_id
        assert shape(payload["geometry"]).is_valid
        assert shape(payload["metadata"]["baseline_geometry"]).is_valid
        assert all(0 <= float(payload[key]) <= 1 for key in scores)
        ids.append(parcel_id)
    assert len(set(ids)) == count

    frame = gpd.GeoDataFrame.from_features(refined["features"], crs="EPSG:4326").to_crs(manifest["crs"])
    assert bool(frame.geometry.is_valid.all())
    assert rl["invalid_after"] == 0
    assert rl["overlap_pairs_after"] <= rl["overlap_pairs_before"]
    assert rl["alignment_after"] >= rl["alignment_before"]
    assert reference["target_reference_used_for_parameter_selection"] is False
    assert rl["reference_used_during_inference"] is False

    with rasterio.open(manifest["image"]) as image, rasterio.open(probability["probability"]) as probabilities:
        assert image.crs == probabilities.crs
        assert image.transform == probabilities.transform
        assert image.shape == probabilities.shape
    policy_hash = hashlib.sha256((ROOT / "checkpoints/ppo_debug_20000.zip").read_bytes()).hexdigest()
    assert policy_hash == rl["policy_sha256"]
    print(json.dumps({
        "parcel_count": count,
        "unique_parcel_ids": len(set(ids)),
        "valid_geometries": int(frame.geometry.is_valid.sum()),
        "alignment_before": rl["alignment_before"],
        "alignment_after": rl["alignment_after"],
        "changed_parcels": rl["changed_parcels"],
        "old_reference_iou": reference["old_cleaned_output"]["harmonic_mean_best_iou"],
        "new_reference_iou_before_rl": reference["new_enclosed_face_vectorization"]["harmonic_mean_best_iou"],
        "new_reference_iou_after_rl": rl["reference_metrics_after_rl"]["harmonic_mean_best_iou"],
        "raster_grid": "pass",
        "policy_sha256": policy_hash,
    }, indent=2))


if __name__ == "__main__":
    main()

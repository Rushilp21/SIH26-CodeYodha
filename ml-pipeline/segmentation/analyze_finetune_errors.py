"""Audit pixel errors per held-out location and OSM hard-negative type."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from model import load_segformer
from finetune_cadastrevision import IGNORE, metrics, probability_tiles, select_threshold, training_masks

ROOT = Path("/home/jl_fs/bhumisetu")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-model", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def feature_audit(model, record: dict, device: str, threshold: float) -> dict:
    _, labels, hard_negative = training_masks(record)
    probabilities = np.zeros(labels.shape, dtype=np.float32)
    row = col = 0
    for probability, tile_labels in probability_tiles(model, [record], device):
        height, width = tile_labels.shape
        probabilities[row:row + height, col:col + width] = probability
        col += width
        if col >= labels.shape[1]:
            col = 0
            row += height
    prediction = probabilities >= threshold
    valid = labels != IGNORE
    result = {}
    for type_id, name in ((1, "road"), (2, "building"), (3, "canal")):
        region = (hard_negative == type_id) & valid
        result[name] = {
            "pixels": int(region.sum()),
            "mean_probability": float(probabilities[region].mean()) if region.any() else None,
            "false_positive_rate": float(prediction[region].mean()) if region.any() else None,
        }
    background = (hard_negative == 0) & valid & (labels == 0)
    result["ordinary_background"] = {
        "pixels": int(background.sum()),
        "mean_probability": float(probabilities[background].mean()) if background.any() else None,
        "false_positive_rate": float(prediction[background].mean()) if background.any() else None,
    }
    return result


def main() -> None:
    args = arguments()
    manifest = json.loads(args.dataset_manifest.read_text())
    records = manifest["records"]
    validation = [record for record in records if record["split"] == "validation"]
    held_out = [record for record in records if record["split"] in {"validation", "test"}]
    baseline, _, _, device = load_segformer(ROOT / "models/segformer_parcel_boundary")
    candidate, _, _, _ = load_segformer(args.candidate_model, device)
    baseline_threshold = select_threshold(baseline, validation, device)["threshold"]
    candidate_threshold = select_threshold(candidate, validation, device)["threshold"]
    report = {
        "baseline_threshold": baseline_threshold,
        "candidate_threshold": candidate_threshold,
        "locations": [],
    }
    for record in held_out:
        report["locations"].append({
            "name": record["name"],
            "split": record["split"],
            "baseline": metrics(baseline, [record], device, baseline_threshold),
            "candidate": metrics(candidate, [record], device, candidate_threshold),
            "baseline_hard_negatives": feature_audit(baseline, record, device, baseline_threshold),
            "candidate_hard_negatives": feature_audit(candidate, record, device, candidate_threshold),
        })
        print("AUDITED", record["name"], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()

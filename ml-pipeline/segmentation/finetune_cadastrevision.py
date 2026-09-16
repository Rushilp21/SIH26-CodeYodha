"""Precision-aware, validation/test-gated SegFormer boundary fine-tuning."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import torch
import torch.nn.functional as F
from rasterio.features import rasterize
from torch.utils.data import DataLoader, Dataset

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from model import load_segformer, model_sha256

ROOT = Path("/home/jl_fs/bhumisetu")
PATCH = 512
IGNORE = 255
MEAN = torch.tensor((0.485, 0.456, 0.406))[:, None, None]
STD = torch.tensor((0.229, 0.224, 0.225))[:, None, None]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="finetune_v3")
    parser.add_argument("--dataset-manifest", type=Path,
                        default=ROOT / "datasets/cadastrevision/finetune_v3/manifest.json")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=26012)
    parser.add_argument("--skip-chain-evaluation", action="store_true")
    return parser.parse_args()


def training_masks(record: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a thin boundary target and OSM-derived hard-negative evidence."""
    with rasterio.open(record["image"]) as source:
        image = source.read([1, 2, 3])
        valid = source.dataset_mask() > 0
        transform, shape, crs = source.transform, source.shape, source.crs
        pixel_size = max(abs(float(transform.a)), abs(float(transform.e)))
    line_path = record.get("reference_lines")
    if not line_path:
        raise RuntimeError(f"{record['name']} has no reference_lines contract")
    references = gpd.read_file(line_path).to_crs(crs)
    geometries = []
    for geometry in references.geometry:
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        geometries.append(geometry.boundary if geometry.geom_type in ("Polygon", "MultiPolygon") else geometry)
    mask = rasterize(
        ((geometry, 1) for geometry in geometries), out_shape=shape, transform=transform,
        fill=0, all_touched=True, dtype="uint8",
    )
    negative_path = record.get("hard_negative_features")
    if not negative_path:
        raise RuntimeError(f"{record['name']} has no hard_negative_features contract")
    negatives = gpd.read_file(negative_path).to_crs(crs)
    type_ids = {"road": 1, "building": 2, "canal": 3, "other": 4}
    negative_shapes = []
    for feature in negatives.itertuples():
        geometry = feature.geometry
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        if feature.feature_type == "road":
            geometry = geometry.buffer(3.0)
        elif feature.feature_type == "canal":
            geometry = geometry.buffer(2.0)
        negative_shapes.append((geometry, type_ids[feature.feature_type]))
    hard_negative = rasterize(
        negative_shapes, out_shape=shape, transform=transform, fill=0, all_touched=True, dtype="uint8",
    )
    # Ancillary features may coincide with legal parcel boundaries. Those pixels
    # are never treated as negatives within a four-pixel cadastral safety band.
    protected = rasterize(
        ((geometry.buffer(4 * pixel_size), 1) for geometry in geometries),
        out_shape=shape, transform=transform, fill=0, all_touched=True, dtype="uint8",
    )
    hard_negative[(protected > 0) | ~valid] = 0
    mask[~valid] = IGNORE
    return image, mask, hard_negative


def boundary_mask(record: dict) -> tuple[np.ndarray, np.ndarray]:
    image, mask, _ = training_masks(record)
    return image, mask


class BoundaryPatches(Dataset):
    """All valid patches are retained, including boundary-free hard negatives."""
    def __init__(self, records: list[dict], augment: bool):
        self.augment = augment
        self.items: list[tuple[np.ndarray, np.ndarray, np.ndarray, str]] = []
        for record in records:
            image, mask, hard_negative = training_masks(record)
            for row in range(0, image.shape[1] - PATCH + 1, PATCH):
                for col in range(0, image.shape[2] - PATCH + 1, PATCH):
                    patch_mask = mask[row:row + PATCH, col:col + PATCH]
                    if np.mean(patch_mask != IGNORE) >= 0.8:
                        patch_hard = hard_negative[row:row + PATCH, col:col + PATCH]
                        present = [name for value, name in ((1, "road"), (2, "building"), (3, "canal"), (4, "other"))
                                   if np.any(patch_hard == value)]
                        category = "+".join(present) if present else "ordinary"
                        item = (image[:, row:row + PATCH, col:col + PATCH], patch_mask, patch_hard, category)
                        self.items.append(item)
                        # Explicitly oversample confusing, mostly boundary-free
                        # urban/water patches without inventing new labels.
                        if np.count_nonzero(patch_hard) >= 500 and np.mean(patch_mask == 1) <= 0.02:
                            self.items.append(item)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        image, mask, hard_negative, _ = self.items[index]
        image, mask, hard_negative = image.copy(), mask.copy(), hard_negative.copy()
        if self.augment and random.random() < 0.5:
            image, mask, hard_negative = image[:, :, ::-1].copy(), mask[:, ::-1].copy(), hard_negative[:, ::-1].copy()
        if self.augment and random.random() < 0.5:
            image, mask, hard_negative = image[:, ::-1, :].copy(), mask[::-1, :].copy(), hard_negative[::-1, :].copy()
        pixels = (torch.from_numpy(image).float().div_(255.0) - MEAN) / STD
        return pixels, torch.from_numpy(mask.astype(np.int64)), torch.from_numpy(hard_negative.astype(np.uint8))


def probability_tiles(model, records: list[dict], device: str):
    model.eval()
    with torch.inference_mode():
        for record in records:
            image, mask = boundary_mask(record)
            for row in range(0, image.shape[1], PATCH):
                for col in range(0, image.shape[2], PATCH):
                    tile = image[:, row:row + PATCH, col:col + PATCH]
                    labels = mask[row:row + PATCH, col:col + PATCH]
                    pixels = (torch.from_numpy(tile).float().div_(255.0) - MEAN) / STD
                    logits = model(pixel_values=pixels[None].to(device)).logits
                    probability = F.interpolate(
                        logits, labels.shape, mode="bilinear", align_corners=False
                    ).softmax(1)[0, 1].cpu().numpy()
                    yield probability, labels


def metrics(model, records: list[dict], device: str, threshold: float) -> dict:
    true_positive = predicted = expected = union = true_negative = false_positive = 0
    for probability, labels in probability_tiles(model, records, device):
        valid, truth = labels != IGNORE, labels == 1
        prediction = (probability >= threshold) & valid
        truth &= valid
        both = prediction & truth
        true_positive += int(both.sum())
        predicted += int(prediction.sum())
        expected += int(truth.sum())
        union += int((prediction | truth).sum())
        false_positive += int((prediction & ~truth & valid).sum())
        true_negative += int((~prediction & ~truth & valid).sum())
    precision = true_positive / max(predicted, 1)
    recall = true_positive / max(expected, 1)
    return {
        "threshold": threshold, "boundary_iou": true_positive / max(union, 1),
        "boundary_f1": 2 * precision * recall / max(precision + recall, 1e-12),
        "precision": precision, "recall": recall,
        "false_positive_rate": false_positive / max(false_positive + true_negative, 1),
        "predicted_boundary_pixels": predicted, "reference_boundary_pixels": expected,
    }


def select_threshold(model, validation: list[dict], device: str) -> dict:
    candidates = [metrics(model, validation, device, round(float(value), 2)) for value in np.arange(0.30, 0.76, 0.05)]
    # Thin-boundary IoU is noisy. Treat thresholds within 0.001 of the optimum
    # as equivalent, then choose the higher-precision, lower-FPR operating point.
    best_iou = max(item["boundary_iou"] for item in candidates)
    near_best = [item for item in candidates if item["boundary_iou"] >= best_iou - 0.001]
    return max(
        near_best,
        key=lambda item: (item["precision"], -item["false_positive_rate"], item["threshold"]),
    )


def boundary_loss(logits, labels, hard_negative, positive_weight: float):
    logits = F.interpolate(logits, labels.shape[-2:], mode="bilinear", align_corners=False)
    valid = labels != IGNORE
    truth = ((labels == 1) & valid).float()
    probability = logits.softmax(1)[:, 1] * valid
    cross_entropy = F.cross_entropy(
        logits, labels, weight=torch.tensor((1.0, positive_weight), device=logits.device), ignore_index=IGNORE,
    )
    true_positive = (probability * truth).sum()
    false_positive = (probability * (1 - truth) * valid).sum()
    false_negative = ((1 - probability) * truth).sum()
    dice = 1 - (2 * true_positive + 1) / (2 * true_positive + false_positive + false_negative + 1)
    # Tversky alpha > beta makes false-positive pixels more expensive.
    tversky = 1 - (true_positive + 1) / (true_positive + 0.75 * false_positive + 0.25 * false_negative + 1)
    dilated_probability = F.max_pool2d(probability[:, None], 3, stride=1, padding=1)[:, 0]
    continuity = 1 - ((dilated_probability * truth).sum() + 1) / (truth.sum() + 1)
    hard = (hard_negative > 0).float() * valid
    hard_negative_penalty = (probability * hard).sum() / (hard.sum() + 1)
    return (0.35 * cross_entropy + 0.20 * dice + 0.25 * tversky
            + 0.10 * continuity + 0.10 * hard_negative_penalty)


def main() -> None:
    args = arguments()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.deterministic = True
    manifest = json.loads(args.dataset_manifest.read_text())
    records = manifest["records"]
    training = [record for record in records if record["split"] == "train"]
    validation = [record for record in records if record["split"] == "validation"]
    test = [record for record in records if record["split"] == "test"]
    if len(training) < 9 or len(validation) < 3 or len(test) < 3:
        raise RuntimeError("Proper fine-tuning requires at least 9 train, 3 validation, and 3 test windows")
    legacy_target_use = manifest.get("target_aoi_used_for_training_or_selection")
    target_selection = manifest.get("target_aoi_used_for_parameter_selection", legacy_target_use)
    target_test = manifest.get("target_aoi_used_for_test", legacy_target_use)
    if target_selection is not False or target_test is not False:
        raise RuntimeError("Dataset manifest does not prove target-AOI exclusion from validation and test")
    feedback_records = [record for record in records if record.get("source") == "human_review_feedback"]
    if any(record.get("split") != "train" for record in feedback_records):
        raise RuntimeError("Human review feedback is permitted only in the training split")

    baseline_dir = ROOT / "models/segformer_parcel_boundary"
    result_dir = ROOT / "results" / f"segformer_{args.version}"
    candidate_dir = ROOT / "models" / f"segformer_parcel_boundary_{args.version}"
    result_dir.mkdir(parents=True, exist_ok=True)
    if candidate_dir.exists():
        raise RuntimeError(f"Refusing to overwrite {candidate_dir}")
    model, processor, boundary_channel, device = load_segformer(baseline_dir)
    if boundary_channel != 1:
        raise RuntimeError("Training contract currently requires parcel_boundary channel 1")
    baseline_validation = select_threshold(model, validation, device)
    baseline_test = metrics(model, test, device, baseline_validation["threshold"])

    for parameter in model.parameters():
        parameter.requires_grad = False
    for module in (model.decode_head, model.segformer.encoder.block[-1], model.segformer.encoder.layer_norm[-1]):
        for parameter in module.parameters():
            parameter.requires_grad = True
    dataset = BoundaryPatches(training, augment=True)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)
    positive = sum(int((mask == 1).sum()) for _, mask, _, _ in dataset.items)
    negative = sum(int((mask == 0).sum()) for _, mask, _, _ in dataset.items)
    positive_weight = float(np.clip(negative / max(positive, 1), 2, 8))
    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=args.learning_rate, weight_decay=0.01,
    )

    history, best_score, best_epoch, stale = [], -1.0, 0, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for pixels, labels, hard_negative in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = boundary_loss(
                model(pixel_values=pixels.to(device, non_blocking=True)).logits,
                labels.to(device, non_blocking=True), hard_negative.to(device, non_blocking=True), positive_weight,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 1.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        validation_metrics = select_threshold(model, validation, device)
        score = validation_metrics["boundary_iou"] + 0.20 * validation_metrics["precision"]
        epoch_report = {"epoch": epoch, "loss": float(np.mean(losses)), "validation": validation_metrics}
        history.append(epoch_report)
        print("EPOCH", json.dumps(epoch_report), flush=True)
        checkpoint = result_dir / "checkpoints" / f"epoch_{epoch:03d}"
        model.save_pretrained(checkpoint)
        processor.save_pretrained(checkpoint)
        if not args.skip_chain_evaluation:
            subprocess.run([
                sys.executable, str(HERE / "evaluate_model_chain.py"),
                "--model-dir", str(checkpoint), "--dataset-manifest", str(args.dataset_manifest),
                "--version", f"{args.version}_epoch_{epoch:03d}", "--run-ppo",
            ], cwd=ROOT / "repo", check=True)
        if score > best_score + 1e-6:
            best_score, best_epoch, stale = score, epoch, 0
            model.save_pretrained(candidate_dir)
            processor.save_pretrained(candidate_dir)
        else:
            stale += 1
            if stale >= args.patience:
                print(f"EARLY STOP epoch={epoch} best_epoch={best_epoch}", flush=True)
                break

    candidate, _, _, _ = load_segformer(candidate_dir, device)
    candidate_validation = select_threshold(candidate, validation, device)
    candidate_test = metrics(candidate, test, device, candidate_validation["threshold"])
    pixel_gate = (
        candidate_validation["boundary_iou"] > baseline_validation["boundary_iou"]
        and candidate_validation["boundary_f1"] > baseline_validation["boundary_f1"]
        and candidate_test["boundary_iou"] > baseline_test["boundary_iou"]
        and candidate_test["boundary_f1"] > baseline_test["boundary_f1"]
        and candidate_test["precision"] >= 0.95 * baseline_test["precision"]
        and candidate_test["false_positive_rate"] < baseline_test["false_positive_rate"]
    )
    report = {
        "version": args.version, "dataset_manifest": str(args.dataset_manifest),
        "training_windows": [record["name"] for record in training],
        "validation_windows": [record["name"] for record in validation],
        "test_windows": [record["name"] for record in test],
        "target_aoi_used_for_training": bool(feedback_records),
        "target_aoi_used_for_parameter_selection": False,
        "target_aoi_used_for_test": False,
        "baseline_model": str(baseline_dir), "baseline_sha256": model_sha256(baseline_dir),
        "candidate_model": str(candidate_dir), "candidate_sha256": model_sha256(candidate_dir),
        "training_patch_count": len(dataset),
        "boundary_free_training_patches": sum(not np.any(mask == 1) for _, mask, _, _ in dataset.items),
        "hard_negative_patch_counts": {
            category: sum(item[3] == category for item in dataset.items)
            for category in sorted({item[3] for item in dataset.items})
        },
        "positive_class_weight": positive_weight,
        "threshold_selection": "max precision within 0.001 absolute IoU of validation optimum",
        "loss": "0.35 weighted CE + 0.20 Dice + 0.25 precision-Tversky(alpha=0.75,beta=0.25) + 0.10 continuity + 0.10 OSM hard-negative penalty",
        "baseline_validation": baseline_validation, "candidate_validation": candidate_validation,
        "baseline_test": baseline_test, "candidate_test": candidate_test,
        "best_epoch": best_epoch, "history": history,
        "pixel_promotion_gate_passed": pixel_gate,
    }
    report_path = result_dir / "training_report.json"
    temporary = report_path.with_suffix(".tmp.json")
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(report_path)
    if not pixel_gate:
        shutil.rmtree(candidate_dir)
        raise RuntimeError("Fine-tuned candidate failed independent pixel gates; baseline remains canonical")
    print("SEGFORMER PIXEL GATE PASS", json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

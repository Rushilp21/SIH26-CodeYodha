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
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from model import load_segformer, model_sha256
from training_policy import chain_selection_gate, sampling_weights, validation_gate, validation_score

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
    parser.add_argument(
        "--base-model-dir",
        type=Path,
        default=ROOT / "models/segformer_parcel_boundary_finetune_v4_calibrated",
        help="Canonical model to fine-tune and use for independent pixel comparisons.",
    )
    parser.add_argument(
        "--baseline-report",
        type=Path,
        default=ROOT / "results/chain_finetune_v4_calibrated/report.json",
        help="Canonical end-to-end report used for per-checkpoint chain deltas.",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument(
        "--feedback-fraction",
        type=float,
        default=0.30,
        help="Expected fraction of sampled patches sourced from human feedback.",
    )
    parser.add_argument(
        "--unfreeze-last-encoder-block",
        action="store_true",
        help="Also tune the last encoder block; disabled by default to reduce overfitting.",
    )
    parser.add_argument("--seed", type=int, default=26012)
    parser.add_argument(
        "--resume-model-dir",
        type=Path,
        help="Checkpoint to continue optimizing while retaining the canonical base model for metric gates.",
    )
    parser.add_argument(
        "--resume-best-model-dir",
        type=Path,
        help="Previously selected best checkpoint to seed the candidate while optimization resumes from a later epoch.",
    )
    parser.add_argument("--start-epoch", type=int, default=1)
    parser.add_argument("--initial-best-epoch", type=int, default=0)
    parser.add_argument("--initial-best-score", type=float, default=-1.0)
    parser.add_argument("--initial-stale", type=int, default=0)
    parser.add_argument("--skip-chain-evaluation", action="store_true")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run exactly one train epoch and validation pass without creating or promoting a candidate model.",
    )
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
    """Retain valid patches and record source/role for balanced sampling."""
    def __init__(self, records: list[dict], augment: bool):
        self.augment = augment
        self.items: list[tuple[np.ndarray, np.ndarray, np.ndarray, str, str, str]] = []
        for record in records:
            image, mask, hard_negative = training_masks(record)
            source_group = "feedback" if record.get("source") == "human_review_feedback" else "reference"
            for row in range(0, image.shape[1] - PATCH + 1, PATCH):
                for col in range(0, image.shape[2] - PATCH + 1, PATCH):
                    patch_mask = mask[row:row + PATCH, col:col + PATCH]
                    if np.mean(patch_mask != IGNORE) >= 0.8:
                        patch_hard = hard_negative[row:row + PATCH, col:col + PATCH]
                        present = [name for value, name in ((1, "road"), (2, "building"), (3, "canal"), (4, "other"))
                                   if np.any(patch_hard == value)]
                        category = "+".join(present) if present else "ordinary"
                        boundary_pixels = np.count_nonzero(patch_mask == 1)
                        hard_pixels = np.count_nonzero(patch_hard)
                        role = (
                            "positive_boundary" if boundary_pixels >= 32
                            else "hard_negative" if hard_pixels >= 500
                            else "ordinary"
                        )
                        self.items.append((
                            image[:, row:row + PATCH, col:col + PATCH], patch_mask, patch_hard,
                            category, source_group, role,
                        ))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        image, mask, hard_negative, _, _, _ = self.items[index]
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
    # A precision-oriented Tversky term suppresses building/road/canal edges
    # that otherwise dominate after target-feedback fine-tuning.
    tversky = 1 - (true_positive + 1) / (true_positive + 0.85 * false_positive + 0.15 * false_negative + 1)
    dilated_probability = F.max_pool2d(probability[:, None], 3, stride=1, padding=1)[:, 0]
    continuity = 1 - ((dilated_probability * truth).sum() + 1) / (truth.sum() + 1)
    hard = (hard_negative > 0).float() * valid
    hard_negative_penalty = (probability * hard).sum() / (hard.sum() + 1)
    return (0.35 * cross_entropy + 0.20 * dice + 0.25 * tversky
            + 0.10 * continuity + 0.10 * hard_negative_penalty)


def main() -> None:
    args = arguments()
    if args.smoke_test:
        args.epochs = 1
        args.patience = 1
        args.skip_chain_evaluation = True
        if not torch.cuda.is_available():
            raise RuntimeError("Smoke test requires CUDA so it can verify the intended Jarvis GPU path")
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

    baseline_dir = args.base_model_dir
    if not args.smoke_test and not args.baseline_report.is_file():
        raise FileNotFoundError(f"Canonical chain baseline report is missing: {args.baseline_report}")
    result_suffix = f"segformer_{args.version}_smoke" if args.smoke_test else f"segformer_{args.version}"
    result_dir = ROOT / "results" / result_suffix
    candidate_dir = ROOT / "models" / f"segformer_parcel_boundary_{args.version}"
    result_dir.mkdir(parents=True, exist_ok=True)
    if candidate_dir.exists() and not args.smoke_test:
        raise RuntimeError(f"Refusing to overwrite {candidate_dir}")
    model, processor, boundary_channel, device = load_segformer(baseline_dir)
    if boundary_channel != 1:
        raise RuntimeError("Training contract currently requires parcel_boundary channel 1")
    baseline_validation = select_threshold(model, validation, device)
    # A smoke run verifies only the train/validation systems path. Keep the
    # independent test split sealed until an actual promotion candidate exists.
    baseline_test = None if args.smoke_test else metrics(
        model, test, device, baseline_validation["threshold"]
    )
    if args.resume_model_dir:
        if not args.resume_model_dir.is_dir():
            raise FileNotFoundError(f"Resume checkpoint is missing: {args.resume_model_dir}")
        if args.start_epoch < 2 or args.initial_best_epoch < 1 or args.initial_best_score < 0:
            raise RuntimeError("Resume requires start-epoch >= 2 plus the preceding best epoch and score")
        model, processor, boundary_channel, device = load_segformer(args.resume_model_dir, device)
        if boundary_channel != 1:
            raise RuntimeError("Resume checkpoint does not use parcel_boundary channel 1")
        if not args.smoke_test:
            best_model_dir = args.resume_best_model_dir or args.resume_model_dir
            if not best_model_dir.is_dir():
                raise FileNotFoundError(f"Resume best checkpoint is missing: {best_model_dir}")
            shutil.copytree(best_model_dir, candidate_dir)
    elif not args.smoke_test:
        # A rejected experiment must always fall back to a byte-for-byte copy
        # of the canonical model rather than leaving a partially trained model.
        shutil.copytree(baseline_dir, candidate_dir)

    for parameter in model.parameters():
        parameter.requires_grad = False
    trainable_modules = [model.decode_head]
    if args.unfreeze_last_encoder_block:
        trainable_modules.extend((model.segformer.encoder.block[-1], model.segformer.encoder.layer_norm[-1]))
    for module in trainable_modules:
        for parameter in module.parameters():
            parameter.requires_grad = True
    dataset = BoundaryPatches(training, augment=True)
    weights = sampling_weights(
        [(source_group, role) for _, _, _, _, source_group, role in dataset.items],
        feedback_fraction=args.feedback_fraction,
    )
    sampler = WeightedRandomSampler(
        weights, num_samples=len(dataset), replacement=True,
        generator=torch.Generator().manual_seed(args.seed),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, sampler=sampler, num_workers=2, pin_memory=True)
    positive = sum(int((mask == 1).sum()) for _, mask, _, _, _, _ in dataset.items)
    negative = sum(int((mask == 0).sum()) for _, mask, _, _, _, _ in dataset.items)
    positive_weight = float(np.clip(negative / max(positive, 1), 1.5, 4))
    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=args.learning_rate, weight_decay=0.01,
    )

    history = []
    best_score = max(validation_score(baseline_validation), args.initial_best_score) if args.resume_model_dir else validation_score(baseline_validation)
    best_epoch = args.initial_best_epoch if args.resume_model_dir else 0
    stale = args.initial_stale if args.resume_model_dir else 0
    selected_checkpoint_chain_eligible = False
    selected_chain_report_path = None
    selected_final_promotion_eligible = False
    for epoch in range(args.start_epoch, args.epochs + 1):
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
        score = validation_score(validation_metrics)
        pixel_selection_eligible = validation_gate(validation_metrics, baseline_validation)
        epoch_report = {
            "epoch": epoch,
            "loss": float(np.mean(losses)),
            "validation": validation_metrics,
            "validation_score": score,
            "validation_gate_passed": pixel_selection_eligible,
            "chain_evaluation": {"status": "pending"},
        }
        print("EPOCH", json.dumps(epoch_report), flush=True)
        checkpoint = result_dir / "checkpoint"
        if not args.smoke_test:
            checkpoint = result_dir / "checkpoints" / f"epoch_{epoch:03d}"
        model.save_pretrained(checkpoint)
        processor.save_pretrained(checkpoint)
        chain_eligible = False
        chain_report = None
        chain_report_path = None
        if not args.skip_chain_evaluation:
            chain_version = f"{args.version}_epoch_{epoch:03d}"
            try:
                subprocess.run([
                    sys.executable, str(HERE / "evaluate_model_chain.py"),
                    "--model-dir", str(checkpoint), "--dataset-manifest", str(args.dataset_manifest),
                    "--version", chain_version, "--run-ppo",
                    "--baseline-report", str(args.baseline_report),
                ], cwd=ROOT / "repo", check=True)
                chain_report_path = ROOT / "results" / f"chain_{chain_version}" / "report.json"
                chain_report = json.loads(chain_report_path.read_text())
                chain_eligible = chain_selection_gate(chain_report)
                epoch_report["chain_evaluation"] = {
                    "status": "passed",
                    "version": chain_version,
                    "report": str(chain_report_path),
                    "selection_eligible_without_target": chain_eligible,
                }
            except subprocess.CalledProcessError as error:
                epoch_report["chain_evaluation"] = {
                    "status": "failed",
                    "version": chain_version,
                    "returncode": error.returncode,
                    "reason": "Checkpoint did not complete the full probability-to-PPO evaluation chain",
                }
                print("CHAIN EVALUATION REJECTED", json.dumps(epoch_report["chain_evaluation"]), flush=True)
        else:
            epoch_report["chain_evaluation"] = {"status": "skipped"}
        selection_eligible = pixel_selection_eligible and chain_eligible
        epoch_report["selection_eligible"] = selection_eligible
        if selection_eligible and score > best_score + 1e-6:
            best_score, best_epoch, stale = score, epoch, 0
            selected_checkpoint_chain_eligible = True
            selected_chain_report_path = str(chain_report_path)
            selected_final_promotion_eligible = bool(
                chain_report["baseline_comparison"].get("final_promotion_eligible", False)
            )
            if not args.smoke_test:
                model.save_pretrained(candidate_dir)
                processor.save_pretrained(candidate_dir)
        else:
            stale += 1
        print("EPOCH RESULT", json.dumps(epoch_report), flush=True)
        history.append(epoch_report)
        if stale >= args.patience:
            print(f"EARLY STOP epoch={epoch} best_epoch={best_epoch}", flush=True)
            break

    if args.smoke_test:
        if not history:
            raise RuntimeError("Smoke test completed no training epochs")
        final_validation = history[-1]["validation"]
        smoke_report = {
            "schema_version": "bhumisetu.training-smoke.v1",
            "status": "passed",
            "purpose": "One-epoch systems check only; this checkpoint is not eligible for promotion.",
            "dataset_manifest": str(args.dataset_manifest),
            "device": str(device),
            "cuda_available": bool(torch.cuda.is_available()),
            "training_windows": [record["name"] for record in training],
            "validation_windows": [record["name"] for record in validation],
            "test_windows_evaluated": [],
            "training_patch_count": len(dataset),
            "batches": len(loader),
            "loss_finite": bool(np.isfinite(history[-1]["loss"])),
            "loss": history[-1]["loss"],
            "baseline_validation": baseline_validation,
            "post_smoke_validation": final_validation,
            "checkpoint": str(result_dir / "checkpoint"),
            "promotion_attempted": False,
        }
        if not smoke_report["loss_finite"]:
            raise RuntimeError("Smoke test produced no finite training loss")
        report_path = result_dir / "smoke_report.json"
        temporary = report_path.with_suffix(".tmp.json")
        temporary.write_text(json.dumps(smoke_report, indent=2))
        temporary.replace(report_path)
        print("SEGFORMER SMOKE PASS", json.dumps(smoke_report, indent=2), flush=True)
        return

    candidate, _, _, _ = load_segformer(candidate_dir, device)
    candidate_validation = select_threshold(candidate, validation, device)
    assert baseline_test is not None
    candidate_test = metrics(candidate, test, device, candidate_validation["threshold"])
    pixel_gate = (
        selected_checkpoint_chain_eligible
        and candidate_validation["boundary_iou"] > baseline_validation["boundary_iou"]
        and candidate_validation["boundary_f1"] > baseline_validation["boundary_f1"]
        and candidate_test["boundary_iou"] > baseline_test["boundary_iou"]
        and candidate_test["boundary_f1"] > baseline_test["boundary_f1"]
        and candidate_test["precision"] >= 0.95 * baseline_test["precision"]
        and candidate_test["false_positive_rate"] < baseline_test["false_positive_rate"]
    )
    end_to_end_gate = pixel_gate and selected_final_promotion_eligible
    report = {
        "version": args.version, "dataset_manifest": str(args.dataset_manifest),
        "training_windows": [record["name"] for record in training],
        "validation_windows": [record["name"] for record in validation],
        "test_windows": [record["name"] for record in test],
        "target_aoi_used_for_training": bool(feedback_records),
        "target_aoi_used_for_parameter_selection": False,
        "target_aoi_used_for_test": False,
        "resumed_from_checkpoint": str(args.resume_model_dir) if args.resume_model_dir else None,
        "resumed_best_checkpoint": str(args.resume_best_model_dir) if args.resume_best_model_dir else None,
        "start_epoch": args.start_epoch,
        "initial_best_epoch": args.initial_best_epoch if args.resume_model_dir else None,
        "initial_best_score": args.initial_best_score if args.resume_model_dir else None,
        "baseline_model": str(baseline_dir), "baseline_sha256": model_sha256(baseline_dir),
        "baseline_chain_report": str(args.baseline_report),
        "candidate_model": str(candidate_dir), "candidate_sha256": model_sha256(candidate_dir),
        "training_patch_count": len(dataset),
        "boundary_free_training_patches": sum(not np.any(mask == 1) for _, mask, _, _, _, _ in dataset.items),
        "hard_negative_patch_counts": {
            category: sum(item[3] == category for item in dataset.items)
            for category in sorted({item[3] for item in dataset.items})
        },
        "source_patch_counts": {
            source: sum(item[4] == source for item in dataset.items)
            for source in sorted({item[4] for item in dataset.items})
        },
        "patch_role_counts": {
            role: sum(item[5] == role for item in dataset.items)
            for role in sorted({item[5] for item in dataset.items})
        },
        "feedback_sampling_fraction": args.feedback_fraction,
        "trainable_modules": (
            "decode_head + last_encoder_block" if args.unfreeze_last_encoder_block else "decode_head_only"
        ),
        "learning_rate": args.learning_rate,
        "positive_class_weight": positive_weight,
        "threshold_selection": "max precision within 0.001 absolute IoU of validation optimum",
        "loss": "0.35 weighted CE + 0.20 Dice + 0.25 precision-Tversky(alpha=0.85,beta=0.15) + 0.10 continuity + 0.10 hard-negative penalty",
        "baseline_validation": baseline_validation, "candidate_validation": candidate_validation,
        "baseline_test": baseline_test, "candidate_test": candidate_test,
        "best_epoch": best_epoch, "history": history,
        "selected_checkpoint_chain_eligible": selected_checkpoint_chain_eligible,
        "selected_chain_report": selected_chain_report_path,
        "selected_chain_final_promotion_eligible": selected_final_promotion_eligible,
        "pixel_promotion_gate_passed": pixel_gate,
        "end_to_end_promotion_gate_passed": end_to_end_gate,
    }
    report_path = result_dir / "training_report.json"
    temporary = report_path.with_suffix(".tmp.json")
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(report_path)
    if not end_to_end_gate:
        shutil.rmtree(candidate_dir)
        raise RuntimeError("Fine-tuned candidate failed independent pixel or end-to-end gates; baseline remains canonical")
    print("SEGFORMER END-TO-END GATE PASS", json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

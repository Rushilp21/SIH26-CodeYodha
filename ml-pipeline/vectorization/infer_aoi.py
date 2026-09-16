"""Run the frozen SegFormer model on the bounded vectorization AOI."""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
import torch
import torch.nn.functional as F
from transformers import AutoImageProcessor, SegformerForSemanticSegmentation

ROOT = Path("/home/jl_fs/bhumisetu")
AOI = ROOT / "datasets/cadastrevision/vectorization_v2"
OUTPUT = ROOT / "probability_maps/vectorization_v2_boundary.tif"


def main() -> None:
    manifest = json.loads((AOI / "manifest.json").read_text())
    candidates = [
        path.parent
        for path in (ROOT / "models").rglob("config.json")
        if (path.parent / "model.safetensors").exists()
        and (path.parent / "preprocessor_config.json").exists()
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one frozen SegFormer model, found {len(candidates)}")
    model_dir = candidates[0]
    model_hash = hashlib.sha256((model_dir / "model.safetensors").read_bytes()).hexdigest()

    if OUTPUT.exists():
        with rasterio.open(manifest["image"]) as image, rasterio.open(OUTPUT) as probability:
            if image.crs == probability.crs and image.transform == probability.transform and image.shape == probability.shape:
                print("AOI PROBABILITY EXISTS", OUTPUT, model_hash, flush=True)
                return
        raise RuntimeError("Existing AOI probability map does not match the imagery grid")

    processor = AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(model_dir, local_files_only=True)
    channels = [int(key) for key, value in model.config.id2label.items() if value == "parcel_boundary"]
    if len(channels) != 1:
        raise RuntimeError("The parcel_boundary class is ambiguous")
    model.requires_grad_(False).eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp.tif")

    with rasterio.open(manifest["image"]) as source:
        profile = source.profile.copy()
        profile.update(count=1, dtype="float32", nodata=-9999, compress="deflate", BIGTIFF="IF_SAFER")
        completed = 0
        total = ((source.height + 511) // 512) * ((source.width + 511) // 512)
        with rasterio.open(temporary, "w", **profile) as destination:
            for row in range(0, source.height, 512):
                for col in range(0, source.width, 512):
                    window = Window(col, row, min(512, source.width - col), min(512, source.height - row))
                    left, top = max(0, col - 32), max(0, row - 32)
                    context = Window(
                        left,
                        top,
                        min(source.width, col + window.width + 32) - left,
                        min(source.height, row + window.height + 32) - top,
                    )
                    rgb = source.read([1, 2, 3], window=context)
                    if rgb.dtype != np.uint8:
                        raise RuntimeError("AOI imagery needs explicit radiometric calibration")
                    inputs = processor(images=rgb, return_tensors="pt")
                    with torch.inference_mode():
                        logits = model(**{key: value.to(device) for key, value in inputs.items()}).logits
                        logits = F.interpolate(
                            logits,
                            size=(int(context.height), int(context.width)),
                            mode="bilinear",
                            align_corners=False,
                        )
                        probabilities = logits.softmax(1)[0, channels[0]].cpu().numpy()
                    probabilities = probabilities[
                        row - top : row - top + int(window.height),
                        col - left : col - left + int(window.width),
                    ]
                    probabilities[source.dataset_mask(window=window) == 0] = -9999
                    destination.write(probabilities.astype("float32"), 1, window=window)
                    completed += 1
                    if completed % 25 == 0 or completed == total:
                        print(f"AOI INFERENCE {completed}/{total}", flush=True)
    temporary.replace(OUTPUT)
    with rasterio.open(manifest["image"]) as image, rasterio.open(OUTPUT) as probability:
        assert image.crs == probability.crs and image.transform == probability.transform
        assert image.shape == probability.shape
    (AOI / "probability.json").write_text(json.dumps({
        "probability": str(OUTPUT),
        "model": str(model_dir),
        "model_sha256": model_hash,
        "frozen": True,
        "boundary_class": channels[0],
    }, indent=2))
    print("AOI PROBABILITY PASS", OUTPUT, model_hash, flush=True)


if __name__ == "__main__":
    main()

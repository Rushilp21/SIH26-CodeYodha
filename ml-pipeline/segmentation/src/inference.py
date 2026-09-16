"""Georeferenced tiled inference shared by training evaluation and production."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
import torch
import torch.nn.functional as F


def infer_probability_raster(
    model,
    processor,
    boundary_channel: int,
    device: str,
    image_path: str | Path,
    output_path: str | Path,
    tile_size: int = 512,
) -> Path:
    """Write one boundary-probability GeoTIFF on exactly the source raster grid."""
    image_path, output_path = Path(image_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    model.eval()
    with rasterio.open(image_path) as source:
        profile = source.profile.copy()
        profile.update(count=1, dtype="float32", nodata=-9999, compress="deflate", BIGTIFF="IF_SAFER")
        with rasterio.open(temporary, "w", **profile) as destination:
            for row in range(0, source.height, tile_size):
                for col in range(0, source.width, tile_size):
                    window = Window(col, row, min(tile_size, source.width - col), min(tile_size, source.height - row))
                    rgb = source.read([1, 2, 3], window=window)
                    inputs = processor(images=np.moveaxis(rgb, 0, -1), return_tensors="pt")
                    with torch.inference_mode():
                        logits = model(**{key: value.to(device) for key, value in inputs.items()}).logits
                        probability = F.interpolate(
                            logits, (int(window.height), int(window.width)), mode="bilinear", align_corners=False
                        ).softmax(1)[0, boundary_channel].cpu().numpy()
                    probability[source.dataset_mask(window=window) == 0] = -9999
                    destination.write(probability.astype("float32"), 1, window=window)
    temporary.replace(output_path)
    with rasterio.open(image_path) as image, rasterio.open(output_path) as probability:
        if image.crs != probability.crs or image.transform != probability.transform or image.shape != probability.shape:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("Output probability grid differs from its source image")
    return output_path

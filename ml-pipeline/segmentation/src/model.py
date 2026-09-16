"""Shared, local-only loading helpers for the frozen SegFormer contract."""

from __future__ import annotations

import hashlib
from pathlib import Path

import torch
from transformers import AutoImageProcessor, SegformerForSemanticSegmentation

REQUIRED_MODEL_FILES = ("config.json", "model.safetensors", "preprocessor_config.json")


def model_sha256(model_dir: str | Path) -> str:
    """Return the immutable weight identity recorded in experiment reports."""
    path = Path(model_dir) / "model.safetensors"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_segformer(model_dir: str | Path, device: str | None = None):
    """Load a locally stored SegFormer and resolve its parcel-boundary channel."""
    model_dir = Path(model_dir)
    missing = [name for name in REQUIRED_MODEL_FILES if not (model_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Incomplete SegFormer model at {model_dir}: {', '.join(missing)}")
    processor = AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(model_dir, local_files_only=True)
    channels = [int(key) for key, value in model.config.id2label.items() if value == "parcel_boundary"]
    if len(channels) != 1:
        raise RuntimeError("The parcel_boundary class is missing or ambiguous")
    resolved_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(resolved_device)
    return model, processor, channels[0], resolved_device

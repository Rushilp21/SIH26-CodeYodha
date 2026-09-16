"""Generate versioned, georeferenced probabilities from a gated candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from inference import infer_probability_raster
from model import load_segformer, model_sha256

ROOT = Path("/home/jl_fs/bhumisetu")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="finetune_v2")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output-version")
    parser.add_argument("--skip-pixel-gate", action="store_true")
    parser.add_argument("--dataset-manifest", type=Path,
                        default=ROOT / "datasets/cadastrevision/finetune_v2/manifest.json")
    args = parser.parse_args()
    model_dir = args.model_dir or ROOT / "models" / f"segformer_parcel_boundary_{args.version}"
    output_version = args.output_version or args.version
    output_dir = ROOT / "probability_maps" / output_version
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    source_manifest = json.loads(args.dataset_manifest.read_text())
    training_report_path = ROOT / "results" / f"segformer_{args.version}" / "training_report.json"
    if not args.skip_pixel_gate:
        training_report = json.loads(training_report_path.read_text())
        if not training_report.get("pixel_promotion_gate_passed"):
            raise RuntimeError("Candidate has not passed the independent pixel promotion gate")
    aoi = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
    model, processor, boundary_channel, device = load_segformer(model_dir)
    model.eval().requires_grad_(False)
    output_records = []
    for record in source_manifest["records"]:
        output = output_dir / f"{record['name']}_boundary.tif"
        infer_probability_raster(model, processor, boundary_channel, device, record["image"], output)
        output_records.append({**record, "probability": str(output)})
        print("PROBABILITY", record["name"], flush=True)
    aoi_output = output_dir / "vectorization_aoi_boundary.tif"
    infer_probability_raster(model, processor, boundary_channel, device, aoi["image"], aoi_output)
    manifest = {
        "model": str(model_dir), "model_sha256": model_sha256(model_dir),
        "fine_tuned": model_dir.resolve() != (ROOT / "models/segformer_parcel_boundary").resolve(),
        "boundary_class": boundary_channel, "records": output_records,
        "aoi_probability": str(aoi_output), "target_aoi_used_for_training_or_selection": False,
        "pixel_gate_report": None if args.skip_pixel_gate else str(training_report_path),
    }
    temporary = output_dir / ".manifest.tmp.json"
    temporary.write_text(json.dumps(manifest, indent=2))
    temporary.replace(output_dir / "manifest.json")
    print("CANDIDATE PROBABILITIES PASS", json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()

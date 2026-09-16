# Segmentation (Developer 1 ONLY)

## Purpose
Parcel / building / road / land-use extraction. Export GeoJSON to Dev 2.

## Owner
Developer 1.

## Inputs
Preprocessed tiles from `ingestion/`.

## Outputs
FeatureCollection matching `shared-schemas/geojson/segmentation-output.schema.json`
Geometry in **EPSG:4326**.

Classes: `parcel`, `building`, `road`, `land_use`.

Communicate via GeoJSON files, not Python imports into Dev 2.

## Tests
`pytest ml-pipeline/segmentation/tests`

## CadastreVision fine-tuning

`prepare_finetune_dataset.py` range-reads ten geographically disjoint,
density-stratified 1536 px CadastreVision windows (6 train, 2 validation, 2
test) directly into persistent Jarvis storage. Target-AOI windows are excluded.
It stores the official cadastral linework as a separate mask contract, so
`finetune_cadastrevision.py` can build thin line targets without buffering parcel
faces. All valid 512 px patches are retained, including boundary-free hard
negatives. Training uses weighted cross-entropy, Dice, and a precision-weighted
Tversky term, early stopping, and an independent test gate. The immutable
baseline is never overwritten.

After the pixel gate passes, `infer_cadastrevision.py` writes versioned,
georeferenced probability rasters for every window and the target AOI. Shared
model loading and tiled inference live in `src/model.py` and `src/inference.py`;
the obsolete placeholder classes were replaced rather than duplicated.

### Proper-training preparation (v3)

The v3 manifest expands to 9 geographically separated training, 3 validation,
and 3 test windows. It records real OpenStreetMap road, building, and waterway
features as ancillary hard-negative evidence (ODbL); a four-pixel safety band
prevents coincident legal boundaries from being mislabeled. Training
oversamples confusing negative patches and combines weighted cross-entropy,
Dice, precision-weighted Tversky, continuity, and hard-negative penalties.

`evaluate_model_chain.py` is the single checkpoint evaluator. For a baseline or
saved epoch it runs pixel metrics, georeferenced inference, multiwindow parcel
vectorization, target-report-only comparison, topology checks, and optional PPO
refinement. The 30-epoch trainer saves each epoch and invokes this full chain by
default; `--skip-chain-evaluation` is intended only for smoke tests.

The frozen v3 baseline is stored in
`results/chain_baseline_finetune_v3/report.json`. Its validation pixel IoU is
`0.0351029`, test pixel IoU is `0.0516160`, and held-out polygon harmonic IoU
is `0.0429216`. On the report-only target, harmonic IoU is `0.0941110` before
PPO and `0.0942399` after PPO, with zero invalid geometries and overlaps. Future
checkpoint reports calculate deltas against this fixed model hash and distinguish
target-free selection eligibility from final promotion eligibility.

Threshold calibration treats validation IoU values within `0.001` of the
optimum as equivalent, then chooses the highest-precision operating point with
false-positive rate as the next tie-breaker. This prevents a negligible
thin-boundary IoU gain from selecting an overly permissive threshold.

### Fine-tune v1 result

The four-epoch candidate improved held-out pixel boundary IoU from `0.0483981`
to `0.0503347` and F1 from `0.0923276` to `0.0958451`. It did not pass the
end-to-end cadastral gate: held-out polygon harmonic IoU was `0.0128498`
versus production v2's `0.0780615`, and target polygon IoU was `0.0359264`
versus `0.0756354`. The baseline model and v2+PPO output therefore remain
canonical; the failed candidate model/probabilities are not production assets.

### Fine-tune v2 result

The 16-epoch precision-aware candidate passed its independent pixel gate.
Validation boundary IoU improved from `0.0583575` to `0.0805425`, and test IoU
from `0.0520509` to `0.0584290`. Test false-positive rate fell from `0.0545221`
to `0.0452168`. It was not promoted because held-out parcel vectorization
harmonic IoU fell from `0.0480821` to `0.0133017`, despite target-AOI post-PPO
IoU improving from `0.0757950` to `0.0912894`. The small JSON reports and the
41 MB reusable labelled dataset remain; failed weights and probability rasters
were removed.

### Calibrated v4 promotion

The v3 epoch-1 weights were retained after error analysis showed that their
road, building, and canal probabilities improved, while the original `0.45`
operating threshold caused excess ordinary-background detections. The
precision-aware near-optimal-IoU rule selects `0.50`. With that calibration,
validation pixel IoU improves by `0.0035702`, test pixel IoU by `0.0027308`,
and test false-positive rate falls by `0.0055700` versus the frozen baseline.
Held-out polygon harmonic IoU improves by `0.0222573`; the report-only target
post-PPO IoU improves by `0.0229972` to `0.1172371`, with zero invalid or
overlapping geometries. The promoted, versioned model is stored at
`models/segformer_parcel_boundary_finetune_v4_calibrated`; the immutable
original model remains available.

### Human-reviewed feedback preparation

The Web-GIS review queue exports only explicit human decisions through
`GET /projects/{project_id}/review-labels/export`. Verified parcel geometry is
marked `positive_boundary`; rejected building, road, canal, and other shapes
are marked `hard_negative`. Untouched AI output is deliberately excluded.

`build_reviewed_dataset.py` converts that export into small georeferenced
training windows and combines them with the existing CadastreVision manifest.
Feedback windows are always train-only. The independent CadastreVision
validation and test locations remain unchanged for threshold selection and
promotion decisions.

This command prepares data only and does not load or train SegFormer:

```bash
/home/jl_fs/bhumisetu/venv/bin/python \
  ml-pipeline/segmentation/build_reviewed_dataset.py \
  --review-export /home/jl_fs/bhumisetu/datasets/review_exports/review-labels.geojson \
  --base-manifest /home/jl_fs/bhumisetu/datasets/cadastrevision/finetune_v3/manifest.json \
  --imagery-manifest /home/jl_fs/bhumisetu/datasets/cadastrevision/vectorization_v2/manifest.json \
  --output-dir /home/jl_fs/bhumisetu/datasets/cadastrevision/reviewed_feedback_v1 \
  --require-ready
```

Inspect `pretraining_report.json` before training. `dataset_ready` is true only
when the export meets review coverage minimums, every reviewed geometry matches
the supplied imagery, feedback windows were produced, and the held-out split
contract remains intact.

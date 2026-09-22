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

`prepare_finetune_dataset.py` range-reads fifteen geographically disjoint,
density-stratified 1536 px CadastreVision windows (9 train, 3 validation, 3
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

### Preflight and smoke test

Run the read-only readiness gate before allocating time to a proper training
run. It validates every referenced file, CRS/transform, split counts and
spatial isolation, thin-mask density, boundary/negative conflicts, and
rasterized road/building/canal coverage. OSM ancillary labels and explicit
human feedback are reported separately.

```bash
/home/jl_fs/bhumisetu/venv/bin/python \
  ml-pipeline/segmentation/check_training_readiness.py \
  --dataset-manifest /home/jl_fs/bhumisetu/datasets/cadastrevision/finetune_v3/manifest.json \
  --output /home/jl_fs/bhumisetu/results/training_readiness/report.json
```

After the preflight passes, `--smoke-test` performs exactly one training epoch
and one validation pass. It deliberately does not inspect the test split,
invoke vectorization/PPO, create a promotable candidate, or alter the canonical
model. The checkpoint exists only for debugging the complete save/load path.

```bash
/home/jl_fs/bhumisetu/venv/bin/python \
  ml-pipeline/segmentation/finetune_cadastrevision.py \
  --version readiness_v1 \
  --dataset-manifest /home/jl_fs/bhumisetu/datasets/cadastrevision/finetune_v3/manifest.json \
  --batch-size 2 \
  --smoke-test
```

For the later heavy-training gate, build a combined reviewed manifest with
`build_reviewed_dataset.py --require-ready`, then rerun the readiness command
with `--require-human-feedback`. Untouched AI parcels must never be promoted to
labels merely to satisfy the minimum.

Heavy training starts from the promoted calibrated v4 model and compares every
checkpoint with `chain_finetune_v4_calibrated/report.json`. Both paths are
explicit trainer arguments so an experiment cannot silently fall back to the
older frozen baseline. A checkpoint is not production merely because the
trainer's pixel gate passes; its end-to-end chain report must also pass the
held-out polygon, topology, test, and PPO promotion gates.

### Conservative reviewed-feedback recipe

Reviewed target-AOI windows can easily overwhelm the geographically independent
CadastreVision windows. The trainer therefore samples reference and feedback
patches with fixed expected mass (70% reference, 30% feedback), then balances
positive-boundary, hard-negative, and ordinary patches within each source. It
does not duplicate geometries or copy reviewed examples into validation/test.

The default optimization recipe is intentionally conservative after the first
reviewed-feedback experiment regressed on independent test and polygon metrics:

- tune only the SegFormer decode head;
- use a `5e-6` learning rate;
- cap positive-class amplification at 4x;
- apply a precision-oriented Tversky term (`alpha=0.85`);
- require validation IoU/F1/precision/FPR improvement;
- require the non-target pixel → polygon → topology chain gate before a
  checkpoint can become the candidate;
- require independent test and target report-only PPO improvement before final
  promotion.

`--unfreeze-last-encoder-block` is an explicit opt-in experiment, not the
default. A rejected run deletes its candidate model and leaves the calibrated
v4 model canonical. Only an end-to-end accepted run should be vectorized and
imported into the Web-GIS for visual comparison.

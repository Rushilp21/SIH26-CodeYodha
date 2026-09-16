# Vectorization + topology (Developer 2 ONLY)

## Purpose
Raster-to-polygon, topology validation. Handoff into RL refinement.

## Owner
Developer 2.

## Inputs
Dev 1 GeoJSON (`segmentation-output.schema.json`). Raster masks if needed.

## Outputs
Valid polygons. Topology flags. Must reproject to `PROCESSING_CRS` for metric checks, then store as `STORAGE_CRS`.

## Evidence-first vectorization flow

The boundary class is vectorized as a line network. The implementation closes
small raster gaps and polygonizes enclosed background faces; it does not turn
foreground connected components into parcel polygons.

Run on Jarvis from the repository root, using the persistent RL environment:

1. `python ml-pipeline/vectorization/prepare_aoi.py`
2. `python ml-pipeline/vectorization/infer_aoi.py`
3. `python ml-pipeline/vectorization/generate_candidates.py`
4. `python ml-pipeline/vectorization/compare_reference.py`
5. Inspect `results/vectorization_v2/reference_comparison.json`.
6. `python ml-pipeline/vectorization/refine_candidates.py`
7. `python ml-pipeline/vectorization/validate_outputs.py`

For a fine-tuned candidate, pass its probability manifest and a new output
version to `generate_candidates.py`, require `compare_reference.py` to pass,
then run `refine_candidates.py --candidate-version ... --probability-manifest
...`. `evaluate_promotion.py` is the final gate: the candidate is eligible only
when independent pixel validation/test, held-out and target vectorization, and
post-PPO target parcel accuracy all improve without topology regression. Failed
candidate weights, probability rasters, and parcel payloads can then be removed
while retaining the small JSON audit reports.

The baseline profile uses `train_selected_0`; the separate validation window
reports generalization, and target reference geometry is used only after
candidate generation for comparison. It never enters selection, policy
observations, or actions.

Persistent outputs are written under
`/home/jl_fs/bhumisetu/results/vectorization_v2`. The PPO step reuses
`/home/jl_fs/bhumisetu/checkpoints/ppo_debug_20000.zip`; it does not retrain.

## Tests

`pytest ml-pipeline/vectorization/tests`

## Frozen-model evidence fusion and promotion gates

The optional candidate flow keeps the frozen SegFormer model and v2 production
result unchanged. The bounded training windows and probability maps are retained
as reusable persistent evidence; one-off v3 experiment drivers are no longer
part of the pipeline.

1. `python ml-pipeline/vectorization/generate_candidates.py --profile fused --output-version vectorization_v4`
2. `python ml-pipeline/vectorization/compare_reference.py --candidate-version vectorization_v4 --baseline-version vectorization_v2`

The fused profile selects morphology and image-gradient fusion parameters using
all available training windows. Validation and target references are report-only
gates. A candidate is never promoted merely because it looks better on the
target AOI: it must retain held-out validation quality, improve target harmonic
best-IoU, and contain no invalid geometry.

Candidate outputs are versioned under `results/vectorization_v4`; they never
overwrite `vectorization_v2`.

### Retired experiment record

The superseded v3 drivers and bulky failed candidates were removed after their
promotion results were recorded here. Production v2 scored `0.0780615` held-out
validation harmonic best-IoU and `0.0756354` on the report-only target. Strict
v3 scored `0.0151059` validation and `0.0549524` target; balanced v3 scored
`0.0520167` validation and `0.0868840` target. Both had zero invalid candidates,
but both failed the required validation gate, so neither was promoted.

Frozen evidence-fusion v4 selected `edge_weight=0.4`, `threshold=0.45`,
`close_pixels=7`, and no boundary dilation across three training windows. It
reduced held-out mean boundary distance from `32.4451 m` to `21.0352 m`, but
held-out harmonic best-IoU fell from `0.0780615` to `0.0676675`. On the
report-only target it scored `0.0745776` versus v2's `0.0756354` and produced
556 candidates versus 106. It therefore failed promotion and v2 remains
canonical. The failed candidate payload was removed after recording these
metrics.

Precision-aware SegFormer fine-tune v2 passed pixel validation/test and reduced
false positives. Multiwindow vectorization produced 155 valid target parcels;
the existing PPO policy safely changed 77, improved evidence alignment from
`0.1503252` to `0.1565768`, and produced no invalid geometries or overlaps.
Target post-PPO harmonic IoU improved to `0.0912894` from production v2's
`0.0757950`, but same-window held-out vectorization fell to `0.0133017` from
`0.0480821`. The strict generalization gate therefore rejected promotion.
Production `vectorization_v2` remains canonical and bulky failed-candidate
artifacts were removed after the audit reports were retained.

The former standalone `simplify.py` utility was removed: it hardcoded retired
raw-data paths and duplicated projected-CRS simplification already enforced by
`src/raster_to_polygon.py`.

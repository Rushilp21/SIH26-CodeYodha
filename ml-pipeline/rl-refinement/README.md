# RL-based parcel boundary refinement (Developer 2 ONLY)

This is a **first-class IP module**, not polygon smoothing.

## Purpose
Gymnasium env + PPO (Stable-Baselines3) to nudge vertices using imagery, elevation, neighbors, topology.

## Owner
Developer 2.

## Inputs
- coarse polygon / segmentation
- imagery patch
- DSM/DTM patch
- neighboring parcel geometry
- topology context
- optional ground truth for IoU reward

## Outputs
Refined geometry + scores matching `shared-schemas/geojson/refined-parcel.schema.json`

## Action space (initial)
Discrete vertex micro-movements. See `src/actions.py`.

## Reward components
`iou`, `edge_alignment`, `regularity`, `topology`, `baseline_deviation` → `RewardBreakdown.total`

## Do not
- Fake PPO training
- Reduce this to Chaikin/smoothing

## Tests
`pytest ml-pipeline/rl-refinement/tests`

## Train later
TODO in `src/agent.py` — PPO once the env observation space is finalized.

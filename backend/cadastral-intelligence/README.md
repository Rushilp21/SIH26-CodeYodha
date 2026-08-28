# Cadastral Intelligence (Developer 3 ONLY)

## Purpose
Discrepancy analysis, change detection, anomaly detection, cadastral health score, survey prioritization.

## Owner
Developer 3. Do **not** import `ml-pipeline/**` code.

## Inputs
Parcel GeoJSON / API payloads (EPSG:4326). Historical versions. Confidence from Dev 2 via backend.

## Outputs
- `health_score` using the frozen formula in `src/health_score.py`
- anomaly records (types frozen)
- priority scores for survey queue

## Dependencies
None on Dev 1/2 packages. Optional Shapely/GeoPandas later for metric work in `PROCESSING_CRS`.

## Tests

```
pytest backend/cadastral-intelligence/tests
```

## Formula (frozen)

```
health = 0.4*confidence + 0.2*(1-topo_flag) + 0.2*(1-discrepancy) + 0.2*(1-volatility)
```

Weights are configurable via `HealthWeights`.

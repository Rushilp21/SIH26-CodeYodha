"""Export FeatureCollection per shared-schemas/geojson/segmentation-output.schema.json."""

import json
from pathlib import Path


def export_geojson(features: list[dict], dest: str | Path) -> None:
    fc = {"type": "FeatureCollection", "features": features}
    Path(dest).write_text(json.dumps(fc), encoding="utf-8")

import importlib.util
from pathlib import Path
import sys

import numpy as np
from affine import Affine

MODULE = Path(__file__).resolve().parents[1] / "src" / "raster_to_polygon.py"
SPEC = importlib.util.spec_from_file_location("raster_to_polygon", MODULE)
VECTORIZE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VECTORIZE
SPEC.loader.exec_module(VECTORIZE)


def test_polygonizes_enclosed_background_face_not_foreground_line():
    probability = np.zeros((64, 64), dtype=np.float32)
    probability[10:12, 10:54] = 0.95
    probability[52:54, 10:54] = 0.95
    probability[10:54, 10:12] = 0.95
    probability[10:54, 52:54] = 0.95
    result = VECTORIZE.raster_to_polygon(
        probability,
        Affine.translation(1000, 2000) @ Affine.scale(1, -1),
        "EPSG:3857",
        VECTORIZE.VectorizationConfig(
            threshold=0.5,
            close_pixels=1,
            boundary_width_pixels=0,
            edge_buffer_pixels=1,
            min_area_m2=100,
            max_area_m2=10_000,
            simplify_tolerance_m=0,
        ),
    )
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["area_m2"] > 1_000
    assert result["features"][0]["geometry"]["type"] == "Polygon"


def test_rejects_unprojected_source_grid():
    probability = np.zeros((16, 16), dtype=np.float32)
    try:
        VECTORIZE.raster_to_polygon(
            probability,
            Affine.translation(4.0, 52.0) @ Affine.scale(0.00001, -0.00001),
            "EPSG:4326",
        )
    except ValueError as error:
        assert "projected" in str(error) or "geotransform" in str(error)
    else:
        raise AssertionError("unprojected raster must be rejected")


def test_filters_implausible_complexity_without_changing_defaults():
    probability = np.zeros((64, 64), dtype=np.float32)
    probability[10:12, 10:54] = 0.95
    probability[52:54, 10:54] = 0.95
    probability[10:54, 10:12] = 0.95
    probability[10:54, 52:54] = 0.95
    transform = Affine.translation(1000, 2000) @ Affine.scale(1, -1)
    accepted = VECTORIZE.raster_to_polygon(
        probability, transform, "EPSG:3857",
        VECTORIZE.VectorizationConfig(threshold=0.5, close_pixels=1, boundary_width_pixels=0,
                                      edge_buffer_pixels=1, min_area_m2=100, max_area_m2=10_000,
                                      simplify_tolerance_m=0, min_compactness=0.5, max_vertices=8),
    )
    rejected = VECTORIZE.raster_to_polygon(
        probability, transform, "EPSG:3857",
        VECTORIZE.VectorizationConfig(threshold=0.5, close_pixels=1, boundary_width_pixels=0,
                                      edge_buffer_pixels=1, min_area_m2=100, max_area_m2=10_000,
                                      simplify_tolerance_m=0, min_compactness=0.9, max_vertices=8),
    )
    assert len(accepted["features"]) == 1
    assert rejected["features"] == []


def test_fuses_image_edges_only_when_explicitly_enabled():
    probability = np.zeros((64, 64), dtype=np.float32)
    image = np.zeros((3, 64, 64), dtype=np.uint8)
    image[:, 10:54, 10:54] = 255
    edges = VECTORIZE.image_edge_evidence(image)
    config = VECTORIZE.VectorizationConfig(
        threshold=0.4, close_pixels=1, boundary_width_pixels=0,
        edge_buffer_pixels=1, min_area_m2=100, max_area_m2=10_000,
        simplify_tolerance_m=0, edge_weight=1.0,
    )
    result = VECTORIZE.raster_to_polygon(
        probability,
        Affine.translation(1000, 2000) @ Affine.scale(1, -1),
        "EPSG:3857",
        config,
        edge_evidence=edges,
    )
    assert len(result["features"]) == 1
    properties = result["features"][0]["properties"]
    assert properties["boundary_alignment_score"] > properties["segformer_boundary_alignment_score"]
    assert properties["raw_confidence"] == properties["segformer_boundary_alignment_score"]


def test_rejects_missing_edge_evidence_for_fused_configuration():
    with np.testing.assert_raises_regex(ValueError, "edge_evidence"):
        VECTORIZE.raster_to_polygon(
            np.zeros((16, 16), dtype=np.float32),
            Affine.translation(1000, 2000) @ Affine.scale(1, -1),
            "EPSG:3857",
            VECTORIZE.VectorizationConfig(edge_weight=0.2),
        )

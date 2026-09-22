"""Contract checks without a database. Live PostGIS checks are separate."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.api.app.main import app
from backend.api.app.schemas.models import GeoJSONGeometry, VerifyIn
from backend.api.app.routers.parcels import verify_parcel
from backend.api.app.routers.parcel_import import PipelineImport, _health_score, _priority, _validate_pipeline_companion
from backend.api.app.routers.projects import _review_export_document
from backend.db.models.orm import Anomaly, ConfidenceEvidence, Correction, ParcelVersion
from backend.db.session import get_db

VALID = {"type": "Polygon", "coordinates": [[[85,23],[85.001,23],[85.001,23.001],[85,23]]]}
PARCEL_ID = "b4201a5c-234a-537b-98b8-685fa76d9e94"


def pipeline_parcel(parcel_id=PARCEL_ID):
    return {
        "parcel_id": parcel_id,
        "geometry": VALID,
        "confidence_score": 0.7,
        "segmentation_score": 0.5,
        "topology_score": 1.0,
        "edge_alignment_score": 0.6,
        "deviation_from_baseline_score": 0.9,
        "explanation": "Frozen model output.",
        "metadata": {
            "baseline_geometry": VALID,
            "policy_sha256": "a" * 64,
            "timesteps": 20000,
            "accepted": True,
            "changed": True,
        },
    }

class Contracts(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_routes_are_registered(self):
        paths = app.openapi()["paths"]
        for route in ["/parcels/{parcel_id}/history", "/parcels/{parcel_id}/comparison", "/projects/{project_id}/parcels/import", "/projects/{project_id}/parcels/pipeline-import", "/projects/{project_id}/review-labels/export", "/projects/{project_id}"]:
            self.assertIn(route, paths)

    def test_review_export_contains_only_explicit_training_labels(self):
        from shapely.geometry import shape
        now = datetime.now(timezone.utc)
        project = SimpleNamespace(id="project-1", name="Reviewed AOI")
        parcels = [
            SimpleNamespace(id="p-positive", project_id="project-1", status="verified", geom=shape(VALID), version=2, source="field_verified", confidence_score=0.8, health_score=0.9),
            SimpleNamespace(id="p-road", project_id="project-1", status="rejected", geom=shape(VALID), version=2, source="ai_extracted", confidence_score=0.4, health_score=0.6),
            SimpleNamespace(id="p-unreviewed", project_id="project-1", status="needs_review", geom=shape(VALID), version=1, source="ai_extracted", confidence_score=0.5, health_score=0.7),
        ]
        corrections = [
            SimpleNamespace(parcel_id="p-positive", correction_type="boundary_adjust", created_at=now),
            SimpleNamespace(parcel_id="p-road", correction_type="reject_road", created_at=now),
        ]
        evidence = [SimpleNamespace(parcel_id="p-road", component="edge_alignment", score=0.1)]
        exported = _review_export_document(project, parcels, corrections, evidence)
        self.assertEqual(exported["schema_version"], "bhumisetu.review-labels.v1")
        self.assertEqual(exported["summary"]["eligible_reviewed_labels"], 2)
        self.assertEqual(exported["summary"]["positive_boundaries"], 1)
        self.assertEqual(exported["summary"]["false_positive_classes"], {"road": 1})
        self.assertEqual({feature["properties"]["training_role"] for feature in exported["features"]}, {"positive_boundary", "hard_negative"})

    def test_pipeline_payload_contract_and_frozen_scores(self):
        payload = PipelineImport.model_validate({"parcels": [pipeline_parcel()]})
        self.assertEqual(len(payload.parcels), 1)
        self.assertEqual(_health_score(0.7, False, 0.1, 0.2), 0.82)
        self.assertEqual(_priority(0.7, 0.1, 0.2, 1, False), 0.2083)

    def test_pipeline_companion_requires_matching_ids_and_geometry(self):
        feature = {"type": "Feature", "geometry": VALID, "properties": {"parcel_id": PARCEL_ID}}
        matching = PipelineImport.model_validate({
            "parcels": [pipeline_parcel()],
            "geojson": {"type": "FeatureCollection", "features": [feature]},
        })
        _validate_pipeline_companion(matching)

        mismatched = PipelineImport.model_validate({
            "parcels": [pipeline_parcel()],
            "geojson": {"type": "FeatureCollection", "features": [{**feature, "properties": {"parcel_id": "3384dc52-f2c1-4051-a6cd-fd2e74fa3881"}}]},
        })
        with self.assertRaises(HTTPException):
            _validate_pipeline_companion(mismatched)

    def test_geometry_validation(self):
        self.assertEqual(GeoJSONGeometry(**VALID).type, "Polygon")
        for invalid in [{"type":"Point","coordinates":[85,23]}, {"type":"Polygon","coordinates":[]}, {"type":"Polygon","coordinates":[[[200,23],[201,23],[201,24],[200,23]]]}]:
            with self.assertRaises(ValueError):
                GeoJSONGeometry(**invalid)

    def test_pipeline_cannot_claim_success(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        response = TestClient(app).post("/projects/test/process")
        self.assertEqual(response.status_code, 501)
        self.assertIn("no processing job", response.json()["detail"])

    def test_reject_does_not_verify(self):
        from shapely.geometry import shape
        db = MagicMock()
        parcel = MagicMock(id="123", geom=shape(VALID), version=1, source="ai_extracted")
        db.get.return_value = parcel
        result = verify_parcel("123", VerifyIn(correction_type="reject"), db)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(parcel.source, "ai_extracted")
        self.assertFalse(any(isinstance(call.args[0], ParcelVersion) for call in db.add.call_args_list))
        db.commit.assert_called_once()

    def test_false_positive_label_is_persisted_as_review_evidence(self):
        from shapely.geometry import shape
        db = MagicMock()
        parcel = MagicMock(id="123", geom=shape(VALID), version=1, source="ai_extracted")
        db.get.return_value = parcel
        result = verify_parcel("123", VerifyIn(correction_type="reject", review_label="false_positive_canal"), db)
        added = [call.args[0] for call in db.add.call_args_list]
        correction = next(item for item in added if isinstance(item, Correction))
        anomaly = next(item for item in added if isinstance(item, Anomaly))
        evidence = next(item for item in added if isinstance(item, ConfidenceEvidence))
        self.assertEqual(correction.correction_type, "reject_canal")
        self.assertEqual(anomaly.type, "false_positive_canal")
        self.assertEqual(evidence.component, "review_label")
        self.assertEqual(result.status, "rejected")

    def test_false_positive_label_requires_rejection(self):
        with self.assertRaises(ValidationError):
            VerifyIn(correction_type="boundary_adjust", review_label="false_positive_road")

    def test_invalid_import_fails_before_database(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        response = TestClient(app).post("/projects/test/parcels/import", json={"type":"FeatureCollection", "features":[]})
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()

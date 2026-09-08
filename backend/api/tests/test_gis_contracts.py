"""Contract checks without a database. Live PostGIS checks are separate."""
import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.api.app.main import app
from backend.api.app.schemas.models import GeoJSONGeometry, VerifyIn
from backend.api.app.routers.parcels import verify_parcel
from backend.db.session import get_db

VALID = {"type": "Polygon", "coordinates": [[[85,23],[85.001,23],[85.001,23.001],[85,23]]]}

class Contracts(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_routes_are_registered(self):
        paths = app.openapi()["paths"]
        for route in ["/parcels/{parcel_id}/history", "/parcels/{parcel_id}/comparison", "/projects/{project_id}/parcels/import"]:
            self.assertIn(route, paths)

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
        db.commit.assert_called_once()

    def test_invalid_import_fails_before_database(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        response = TestClient(app).post("/projects/test/parcels/import", json={"type":"FeatureCollection", "features":[]})
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()

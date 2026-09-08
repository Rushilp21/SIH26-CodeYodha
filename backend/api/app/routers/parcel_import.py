"""Import existing pipeline outputs without claiming a fresh ML/RL execution."""
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from backend.api.app.schemas.models import GeoJSONGeometry
from backend.api.app.services.geo import geojson_to_wkt
from backend.db.models.orm import Project, Parcel, ConfidenceEvidence
from backend.db.session import get_db

router = APIRouter(prefix="/projects", tags=["parcel-import"])

class Feature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: dict = Field(default_factory=dict)

class FeatureCollection(BaseModel):
    type: str
    features: list[Feature] = Field(min_length=1, max_length=5000)

@router.post("/{project_id}/parcels/import")
def import_parcels(project_id: str, body: FeatureCollection, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if body.type != "FeatureCollection" or any(f.type != "Feature" for f in body.features):
        raise HTTPException(422, "Expected a GeoJSON FeatureCollection")
    if db.query(Parcel).filter(Parcel.project_id == project_id).first():
        raise HTTPException(409, "Import requires an empty project to prevent duplicate or overwritten parcels. Create another project.")
    ids = []
    for feature in body.features:
        if feature.properties.get("class", "parcel") != "parcel":
            raise HTTPException(422, "Import parcel-only GeoJSON; mixed segmentation classes are not parcels")
        pid = str(uuid4())
        db.add(Parcel(id=pid, project_id=project_id,
                      geom=WKTElement(geojson_to_wkt(feature.geometry.model_dump()), srid=4326),
                      source="ai_extracted" if "raw_confidence" in feature.properties else "existing_gis",
                      status="needs_review", confidence_score=None, health_score=None, version=1))
        db.flush()
        score = feature.properties.get("raw_confidence")
        if isinstance(score, (float, int)) and not isinstance(score, bool) and 0 <= score <= 1:
            db.add(ConfidenceEvidence(parcel_id=pid, component="segmentation", score=score,
                explanation=f"Imported raw segmentation confidence from tile {str(feature.properties.get('source_tile_id', 'unreported'))[:200]}. This is not boundary confidence or proof of RL execution."))
        ids.append(pid)
    db.flush()
    db.execute(text("UPDATE parcels SET area_sqm=ST_Area(geom::geography) WHERE project_id=CAST(:id AS uuid)"), {"id": project_id})
    project.status = "review"
    db.commit()
    return {"project_id": project_id, "imported": len(ids), "parcel_ids": ids, "provenance": "Imported existing GeoJSON; no new ML/RL execution"}

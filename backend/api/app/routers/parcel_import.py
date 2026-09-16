"""Import existing parcel files and evidence-rich frozen-pipeline outputs."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from backend.api.app.schemas.models import GeoJSONGeometry
from backend.api.app.services.geo import geojson_to_wkt
from backend.db.models.orm import (
    Anomaly,
    ConfidenceEvidence,
    Parcel,
    ParcelVersion,
    Project,
    SurveyQueue,
)
from backend.db.session import get_db

router = APIRouter(prefix="/projects", tags=["parcel-import"])

class Feature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: dict = Field(default_factory=dict)

class FeatureCollection(BaseModel):
    type: str
    features: list[Feature] = Field(min_length=1, max_length=5000)


class PipelineMetadata(BaseModel):
    baseline_geometry: GeoJSONGeometry
    policy_sha256: str = Field(min_length=64, max_length=64)
    timesteps: int = Field(gt=0)
    accepted: bool
    changed: bool


class PipelineParcel(BaseModel):
    parcel_id: str
    geometry: GeoJSONGeometry
    confidence_score: float = Field(ge=0, le=1)
    segmentation_score: float = Field(ge=0, le=1)
    topology_score: float = Field(ge=0, le=1)
    edge_alignment_score: float = Field(ge=0, le=1)
    deviation_from_baseline_score: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=4000)
    demo: bool = False
    metadata: PipelineMetadata


class PipelineImport(BaseModel):
    parcels: list[PipelineParcel] = Field(min_length=1, max_length=5000)
    geojson: FeatureCollection | None = None


def _validate_pipeline_companion(body: PipelineImport) -> None:
    """Prove that an optional display GeoJSON and evidence payload describe the same parcels."""
    if body.geojson is None:
        return
    if body.geojson.type != "FeatureCollection" or any(feature.type != "Feature" for feature in body.geojson.features):
        raise HTTPException(422, "Expected a GeoJSON FeatureCollection companion")
    feature_by_id: dict[str, Feature] = {}
    for feature in body.geojson.features:
        parcel_id = feature.properties.get("parcel_id")
        if not isinstance(parcel_id, str):
            raise HTTPException(422, "Every companion GeoJSON feature must contain properties.parcel_id")
        try:
            parcel_id = str(UUID(parcel_id))
        except ValueError as exc:
            raise HTTPException(422, f"Invalid companion parcel UUID: {parcel_id}") from exc
        if parcel_id in feature_by_id:
            raise HTTPException(422, f"Duplicate companion parcel UUID: {parcel_id}")
        feature_by_id[parcel_id] = feature
    payload_by_id: dict[str, PipelineParcel] = {}
    for item in body.parcels:
        try:
            parcel_id = str(UUID(item.parcel_id))
        except ValueError as exc:
            raise HTTPException(422, f"Invalid refined-payload parcel UUID: {item.parcel_id}") from exc
        if parcel_id in payload_by_id:
            raise HTTPException(422, f"Duplicate parcel UUID in refined payload: {parcel_id}")
        payload_by_id[parcel_id] = item
    if feature_by_id.keys() != payload_by_id.keys():
        missing_metadata = sorted(feature_by_id.keys() - payload_by_id.keys())
        missing_geometry = sorted(payload_by_id.keys() - feature_by_id.keys())
        raise HTTPException(
            422,
            "Companion GeoJSON and refined payload parcel IDs do not match. "
            f"Missing metadata for {missing_metadata[:10]}; missing geometry for {missing_geometry[:10]}",
        )
    for parcel_id, feature in feature_by_id.items():
        feature_shape = shape(feature.geometry.model_dump())
        payload_shape = shape(payload_by_id[parcel_id].geometry.model_dump())
        if not feature_shape.equals_exact(payload_shape, tolerance=1e-12):
            raise HTTPException(422, f"Geometry mismatch for companion parcel {parcel_id}")


def _ensure_empty_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if db.query(Parcel).filter(Parcel.project_id == project_id).first():
        raise HTTPException(409, "Import requires an empty project to prevent duplicate or overwritten parcels. Create another project.")
    return project


def _health_score(confidence: float, topology_violation: bool, discrepancy: float, volatility: float) -> float:
    """Frozen cadastral-intelligence formula documented by Developer 3."""
    return round(max(0.0, min(1.0,
        0.4 * confidence
        + 0.2 * (0.0 if topology_violation else 1.0)
        + 0.2 * (1.0 - discrepancy)
        + 0.2 * (1.0 - volatility)
    )), 4)


def _priority(confidence: float, discrepancy: float, volatility: float, anomaly_count: int, topology_violation: bool) -> float:
    return round(max(0.0, min(1.0,
        0.40 * (1.0 - confidence)
        + 0.25 * discrepancy
        + 0.15 * volatility
        + 0.10 * min(1.0, anomaly_count / 3.0)
        + 0.10 * (1.0 if topology_violation else 0.0)
    )), 4)


def _pipeline_explanations(item: PipelineParcel, discrepancy: float) -> list[tuple[str, float, str]]:
    policy = item.metadata.policy_sha256[:12]
    return [
        ("segmentation", item.segmentation_score, "Calibrated SegFormer boundary-probability alignment stored by the selected vectorization run."),
        ("topology", item.topology_score, "Topology score reported after validity and overlap rejection gates."),
        ("edge_alignment", item.edge_alignment_score, "Refined boundary alignment with local raster edge evidence."),
        ("deviation_from_baseline", item.deviation_from_baseline_score, f"Baseline agreement; measured discrepancy={discrepancy:.4f}."),
        ("rl_refinement", item.edge_alignment_score, f"PPO policy {policy} ran for {item.metadata.timesteps:,} timesteps; candidate accepted={str(item.metadata.accepted).lower()}, changed={str(item.metadata.changed).lower()}. {item.explanation}"),
    ]

@router.post("/{project_id}/parcels/import")
def import_parcels(project_id: str, body: FeatureCollection, db: Session = Depends(get_db)):
    project = _ensure_empty_project(project_id, db)
    if body.type != "FeatureCollection" or any(f.type != "Feature" for f in body.features):
        raise HTTPException(422, "Expected a GeoJSON FeatureCollection")
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


@router.post("/{project_id}/parcels/pipeline-import")
def import_pipeline_parcels(project_id: str, body: PipelineImport, db: Session = Depends(get_db)):
    """Persist already-computed RL output and its real evidence; this does not run a model."""
    project = _ensure_empty_project(project_id, db)
    _validate_pipeline_companion(body)
    if any(item.demo for item in body.parcels):
        raise HTTPException(422, "Demo pipeline payloads are not accepted by the production import endpoint")

    ids: list[str] = []
    for item in body.parcels:
        try:
            parcel_id = str(UUID(item.parcel_id))
        except ValueError as exc:
            raise HTTPException(422, f"Invalid pipeline parcel UUID: {item.parcel_id}") from exc
        if db.get(Parcel, parcel_id) is not None:
            raise HTTPException(409, f"Parcel {parcel_id} is already stored")
        db.add(Parcel(
            id=parcel_id,
            project_id=project_id,
            geom=WKTElement(geojson_to_wkt(item.geometry.model_dump()), srid=4326),
            source="ai_extracted",
            status="ai_processed" if item.confidence_score >= 0.85 else "needs_review",
            confidence_score=item.confidence_score,
            health_score=None,
            version=1,
        ))
        db.add(ParcelVersion(
            parcel_id=parcel_id,
            geom=WKTElement(geojson_to_wkt(item.metadata.baseline_geometry.model_dump()), srid=4326),
            captured_at=datetime.now(timezone.utc),
            source="vectorization_before_rl",
        ))
        ids.append(parcel_id)

    db.flush()
    for item in body.parcels:
        parcel_id = str(UUID(item.parcel_id))
        metrics = db.execute(text("""
            SELECT
              ST_Area(p.geom::geography) AS current_area,
              ST_Area(v.geom::geography) AS baseline_area,
              ST_Area(ST_SymDifference(p.geom, v.geom)::geography) AS difference_area,
              ST_Area(ST_Union(p.geom, v.geom)::geography) AS union_area
            FROM parcels p
            JOIN parcel_versions v ON v.parcel_id = p.id
            WHERE p.id=CAST(:id AS uuid)
            ORDER BY v.captured_at DESC LIMIT 1
        """), {"id": parcel_id}).mappings().one()
        baseline_area = float(metrics["baseline_area"] or 0.0)
        current_area = float(metrics["current_area"] or 0.0)
        area_ratio = min(1.0, abs(current_area - baseline_area) / baseline_area) if baseline_area else 0.0
        boundary_ratio = min(1.0, float(metrics["difference_area"] or 0.0) / float(metrics["union_area"] or 1.0))
        discrepancy = min(1.0, 0.4 * area_ratio + 0.6 * boundary_ratio)
        volatility = area_ratio
        topology_violation = item.topology_score < 0.999

        anomalies: list[tuple[str, float]] = []
        if item.confidence_score < 0.60:
            anomalies.append(("boundary_shift", round(1.0 - item.confidence_score, 4)))
        if discrepancy >= 0.30:
            anomalies.append(("boundary_shift", round(discrepancy, 4)))
        if topology_violation:
            anomalies.append(("topology_break", round(1.0 - item.topology_score, 4)))
        if volatility >= 0.50:
            anomalies.append(("encroachment", round(volatility, 4)))

        parcel = db.get(Parcel, parcel_id)
        parcel.area_sqm = current_area
        parcel.health_score = _health_score(item.confidence_score, topology_violation, discrepancy, volatility)
        for component, score, explanation in _pipeline_explanations(item, discrepancy):
            db.add(ConfidenceEvidence(parcel_id=parcel_id, component=component, score=score, explanation=explanation))
        for anomaly_type, magnitude in anomalies:
            db.add(Anomaly(parcel_id=parcel_id, type=anomaly_type, magnitude=magnitude))

        priority = _priority(item.confidence_score, discrepancy, volatility, len(anomalies), topology_violation)
        reasons = []
        if item.confidence_score < 0.60: reasons.append("low confidence")
        if discrepancy >= 0.30: reasons.append("historical/record discrepancy")
        if volatility >= 0.50: reasons.append("historical instability")
        if anomalies: reasons.append(f"{len(anomalies)} anomaly(s)")
        if topology_violation: reasons.append("topology violation")
        db.add(SurveyQueue(
            parcel_id=parcel_id,
            priority_score=priority,
            reason=", ".join(reasons) if reasons else "low-risk parcel; routine review",
            status="pending",
        ))

    project.status = "review"
    db.commit()
    return {
        "project_id": project_id,
        "imported": len(ids),
        "parcel_ids": ids,
        "provenance": "Imported calibrated SegFormer + PPO payload with matched GeoJSON, stored evidence, and baseline history; no model was run by the API",
    }

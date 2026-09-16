from collections import Counter, defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session


from backend.api.app.schemas.models import (
    ImageryUploadOut,
    ProcessOut,
    ProjectCreate,
    ProjectOut,
    ProjectStatusOut,
)
from backend.api.app.services.geo import geojson_to_wkt, geom_to_geojson
from backend.api.app.tasks.pipeline import process_project as process_project_task
from backend.db.models.orm import ConfidenceEvidence, Correction, Parcel, Project
from backend.db.session import get_db
from celery.result import AsyncResult

router = APIRouter(prefix="/projects", tags=["projects"])

FALSE_POSITIVE_CORRECTIONS = {
    "reject_building": "building",
    "reject_road": "road",
    "reject_canal": "canal",
    "reject_other": "other",
}


def _review_export_document(project, parcels, corrections, evidence_rows) -> dict:
    """Create a portable, training-oriented export from explicit human decisions only."""
    latest_correction = {}
    for correction in sorted(corrections, key=lambda item: item.created_at.timestamp() if item.created_at else 0.0):
        latest_correction[str(correction.parcel_id)] = correction
    evidence_by_parcel = defaultdict(dict)
    for evidence in evidence_rows:
        evidence_by_parcel[str(evidence.parcel_id)][evidence.component] = float(evidence.score)

    features = []
    rejected_without_label = 0
    for parcel in parcels:
        correction = latest_correction.get(str(parcel.id))
        if correction is None:
            continue
        correction_type = str(correction.correction_type)
        if parcel.status == "verified" and not correction_type.startswith("reject"):
            outcome, training_role, false_positive_class = "verified_boundary", "positive_boundary", None
        elif parcel.status == "rejected" and correction_type in FALSE_POSITIVE_CORRECTIONS:
            outcome, training_role = "false_positive", "hard_negative"
            false_positive_class = FALSE_POSITIVE_CORRECTIONS[correction_type]
        else:
            if parcel.status == "rejected":
                rejected_without_label += 1
            continue
        geometry = geom_to_geojson(parcel.geom)
        if geometry is None:
            continue
        reviewed_at = correction.created_at.isoformat() if correction.created_at else None
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "parcel_id": str(parcel.id),
                "project_id": str(parcel.project_id),
                "review_outcome": outcome,
                "training_role": training_role,
                "false_positive_class": false_positive_class,
                "correction_type": correction_type,
                "reviewed_at": reviewed_at,
                "parcel_version": int(parcel.version or 1),
                "source": parcel.source,
                "confidence_score": parcel.confidence_score,
                "health_score": parcel.health_score,
                "evidence": evidence_by_parcel.get(str(parcel.id), {}),
            },
        })

    role_counts = Counter(feature["properties"]["training_role"] for feature in features)
    class_counts = Counter(
        feature["properties"]["false_positive_class"]
        for feature in features if feature["properties"]["false_positive_class"]
    )
    eligible = len(features)
    minimums = {"total": 100, "positive_boundaries": 40, "hard_negatives": 40}
    ready = (
        eligible >= minimums["total"]
        and role_counts["positive_boundary"] >= minimums["positive_boundaries"]
        and role_counts["hard_negative"] >= minimums["hard_negatives"]
    )
    return {
        "schema_version": "bhumisetu.review-labels.v1",
        "type": "FeatureCollection",
        "name": f"{project.name} reviewed parcel feedback",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": {"id": str(project.id), "name": project.name},
        "summary": {
            "project_parcels": len(parcels),
            "eligible_reviewed_labels": eligible,
            "positive_boundaries": role_counts["positive_boundary"],
            "hard_negatives": role_counts["hard_negative"],
            "false_positive_classes": dict(sorted(class_counts.items())),
            "rejected_without_specific_label": rejected_without_label,
            "unreviewed_or_ineligible": len(parcels) - eligible,
            "recommended_minimum": minimums,
            "training_ready": ready,
        },
        "features": features,
    }


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    aoi = None
    if body.area_of_interest:
        aoi = WKTElement(geojson_to_wkt(body.area_of_interest.model_dump()), srid=4326)
    project = Project(id=str(uuid4()), name=body.name, status="created", area_of_interest=aoi)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(
        id=str(project.id),
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        area_of_interest=geom_to_geojson(project.area_of_interest),
        demo=project.name.startswith("DEMO"),
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.created_at.desc()).all()
    return [
        ProjectOut(
            id=str(p.id),
            name=p.name,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
            area_of_interest=geom_to_geojson(p.area_of_interest),
            demo=p.name.startswith("DEMO"),
        )
        for p in rows
    ]


@router.post("/{project_id}/imagery", response_model=ImageryUploadOut)
def upload_imagery(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    raise HTTPException(501, "Raster ingestion is not implemented. Use the parcel GeoJSON import endpoint for existing outputs.")


@router.post("/{project_id}/process", response_model=ProcessOut)
def process_project(project_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="Segmentation inference is unimplemented and trained RL weights are not configured. Import existing parcel GeoJSON to review stored results; no processing job was started.")

@router.get("/{project_id}/task/{task_id}")
def processing_task_status(project_id: str, task_id: str):
    task = AsyncResult(task_id)

    return {
        "project_id": project_id,
        "task_id": task_id,
        "state": task.state,
        "result": task.result if task.successful() else None,
    }

@router.get("/{project_id}/status", response_model=ProjectStatusOut)
def project_status(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    count = db.query(Parcel).filter(Parcel.project_id == project_id).count()
    evidence_count = db.query(ConfidenceEvidence.parcel_id).join(
        Parcel, ConfidenceEvidence.parcel_id == Parcel.id
    ).filter(Parcel.project_id == project_id).distinct().count()
    rl_count = db.query(ConfidenceEvidence.parcel_id).join(
        Parcel, ConfidenceEvidence.parcel_id == Parcel.id
    ).filter(
        Parcel.project_id == project_id,
        ConfidenceEvidence.component == "rl_refinement",
    ).distinct().count()
    return ProjectStatusOut(
        id=str(project.id),
        name=project.name,
        status=project.status,
        parcel_count=count,
        demo=project.name.startswith("DEMO"),
        evidence_parcel_count=evidence_count,
        rl_evidence_parcel_count=rl_count,
        pipeline_provenance=(
            "Frozen SegFormer + PPO vectorization v2 evidence stored"
            if rl_count else None
        ),
    )


@router.get("/{project_id}/review-labels/export")
def export_review_labels(project_id: str, db: Session = Depends(get_db)):
    """Export explicit review decisions without treating untouched model output as ground truth."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    parcels = db.query(Parcel).filter(Parcel.project_id == project_id).all()
    if not parcels:
        return _review_export_document(project, [], [], [])
    parcel_ids = [parcel.id for parcel in parcels]
    corrections = db.query(Correction).filter(Correction.parcel_id.in_(parcel_ids)).all()
    evidence = db.query(ConfidenceEvidence).filter(ConfidenceEvidence.parcel_id.in_(parcel_ids)).all()
    return _review_export_document(project, parcels, corrections, evidence)

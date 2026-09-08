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
from backend.db.models.orm import Parcel, Project
from backend.db.session import get_db
from celery.result import AsyncResult

router = APIRouter(prefix="/projects", tags=["projects"])


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
    return ProjectStatusOut(
        id=str(project.id),
        name=project.name,
        status=project.status,
        parcel_count=count,
        demo=project.name.startswith("DEMO"),
    )

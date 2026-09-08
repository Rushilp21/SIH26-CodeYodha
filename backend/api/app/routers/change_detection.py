from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.app.schemas.models import ChangeDetectionItem
from backend.db.models.orm import Anomaly, Parcel, Project
from backend.db.session import get_db

router = APIRouter(prefix="/change-detection", tags=["change-detection"])


@router.get("", response_model=list[ChangeDetectionItem])
def list_changes(
    project_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Anomaly)
    if since is not None:
        q = q.filter(Anomaly.detected_at >= since)
    rows = q.all()
    if project_id:
        ids = {str(p.id) for p in db.query(Parcel).filter(Parcel.project_id == project_id).all()}
        rows = [r for r in rows if str(r.parcel_id) in ids]
    return [
        ChangeDetectionItem(
            parcel_id=str(r.parcel_id),
            type=r.type,
            magnitude=r.magnitude,
            detected_at=r.detected_at,
            demo=bool((project := db.get(Project, db.get(Parcel, r.parcel_id).project_id)) and project.name.startswith("DEMO")),
        )
        for r in rows
    ]

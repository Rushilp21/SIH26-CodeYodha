from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.app.schemas.models import AssignIn, SurveyQueueItem
from backend.db.models.orm import SurveyQueue
from backend.db.session import get_db

router = APIRouter(prefix="/survey-queue", tags=["survey-queue"])


@router.get("", response_model=list[SurveyQueueItem])
def list_queue(project_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(SurveyQueue)
    rows = q.order_by(SurveyQueue.priority_score.desc()).all()
    items = [
        SurveyQueueItem(
            id=str(r.id),
            parcel_id=str(r.parcel_id),
            priority_score=r.priority_score,
            reason=r.reason,
            status=r.status,
            assigned_to=str(r.assigned_to) if r.assigned_to else None,
            created_at=r.created_at,
        )
        for r in rows
    ]
    if project_id:
        from backend.db.models.orm import Parcel

        parcel_ids = {
            str(p.id) for p in db.query(Parcel).filter(Parcel.project_id == project_id).all()
        }
        items = [i for i in items if i.parcel_id in parcel_ids]
    return items


@router.post("/{item_id}/assign", response_model=SurveyQueueItem)
def assign(item_id: str, body: AssignIn, db: Session = Depends(get_db)):
    row = db.get(SurveyQueue, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    row.assigned_to = body.assigned_to
    row.status = "assigned"
    db.commit()
    db.refresh(row)
    return SurveyQueueItem(
        id=str(row.id),
        parcel_id=str(row.parcel_id),
        priority_score=row.priority_score,
        reason=row.reason,
        status=row.status,
        assigned_to=str(row.assigned_to) if row.assigned_to else None,
        created_at=row.created_at,
    )

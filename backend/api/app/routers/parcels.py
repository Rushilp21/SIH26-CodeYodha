from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from backend.api.app.schemas.models import (
    ExplanationOut,
    EvidenceItem,
    ParcelOut,
    ParcelPatch,
    VerifyIn,
    VerifyOut,
)
from backend.api.app.services.geo import geojson_to_wkt, geom_to_geojson
from backend.api.app.services.parcels import parcel_to_out
from backend.db.models.orm import ConfidenceEvidence, Correction, Parcel
from backend.db.session import get_db

router = APIRouter(prefix="/parcels", tags=["parcels"])


@router.get("", response_model=list[ParcelOut])
def list_parcels(
    project_id: str | None = None,
    status: str | None = None,
    min_confidence: float | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Parcel)
    if project_id:
        q = q.filter(Parcel.project_id == project_id)
    if status:
        q = q.filter(Parcel.status == status)
    if min_confidence is not None:
        q = q.filter(Parcel.confidence_score >= min_confidence)
    rows = q.order_by(Parcel.confidence_score.asc().nullsfirst()).all()
    return [ParcelOut(**parcel_to_out(p)) for p in rows]


@router.get("/{parcel_id}", response_model=ParcelOut)
def get_parcel(parcel_id: str, db: Session = Depends(get_db)):
    p = db.get(Parcel, parcel_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return ParcelOut(**parcel_to_out(p))


@router.patch("/{parcel_id}", response_model=ParcelOut)
def patch_parcel(parcel_id: str, body: ParcelPatch, db: Session = Depends(get_db)):
    p = db.get(Parcel, parcel_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    if body.geom is not None:
        p.geom = WKTElement(geojson_to_wkt(body.geom.model_dump()), srid=4326)
        p.version = (p.version or 1) + 1
    if body.land_use is not None:
        p.land_use = body.land_use
    if body.status is not None:
        p.status = body.status
    db.commit()
    db.refresh(p)
    return ParcelOut(**parcel_to_out(p))


@router.post("/{parcel_id}/verify", response_model=VerifyOut)
def verify_parcel(parcel_id: str, body: VerifyIn, db: Session = Depends(get_db)):
    p = db.get(Parcel, parcel_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    original = geom_to_geojson(p.geom)
    corrected = body.geom.model_dump() if body.geom is not None else original
    correction = Correction(
        id=str(uuid4()),
        parcel_id=p.id,
        original_geom=WKTElement(geojson_to_wkt(original), srid=4326),
        corrected_geom=WKTElement(geojson_to_wkt(corrected), srid=4326),
        correction_type=body.correction_type,
    )
    db.add(correction)
    p.geom = WKTElement(geojson_to_wkt(corrected), srid=4326)
    p.status = "verified"
    p.source = "field_verified"
    p.version = (p.version or 1) + 1
    db.commit()
    return VerifyOut(
        parcel_id=str(p.id),
        status=p.status,
        correction_id=str(correction.id),
        message="Correction recorded. Parcel marked verified.",
    )


@router.get("/{parcel_id}/explanation", response_model=ExplanationOut)
def explanation(parcel_id: str, db: Session = Depends(get_db)):
    p = db.get(Parcel, parcel_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    rows = db.query(ConfidenceEvidence).filter(ConfidenceEvidence.parcel_id == parcel_id).all()
    components = [
        EvidenceItem(component=r.component, score=r.score, explanation=r.explanation) for r in rows
    ]
    narrative = (
        components[-1].explanation
        if components
        else "No evidence rows yet. Seed demo data or wait for Dev 2 RL inference."
    )
    if p.confidence_score is not None and "Boundary" not in narrative:
        narrative = (
            f"Overall confidence {p.confidence_score:.2f}. "
            + " ".join(c.explanation for c in components)
        )
    return ExplanationOut(
        parcel_id=str(p.id),
        explanation=narrative.strip() or "Seeded explanation unavailable.",
        confidence_score=p.confidence_score,
        health_score=p.health_score,
        components=components,
    )

"""Stored geometry versions and comparisons measured with PostGIS geography."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.db.models.orm import Parcel, ParcelVersion
from backend.db.session import get_db
from backend.api.app.services.geo import geom_to_geojson

router = APIRouter(prefix="/parcels", tags=["parcel-history"])

@router.get("/{parcel_id}/history")
def history(parcel_id: str, db: Session = Depends(get_db)):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(404, "Parcel not found")
    rows = db.query(ParcelVersion).filter(ParcelVersion.parcel_id == parcel_id).order_by(ParcelVersion.captured_at.desc()).all()
    return {"parcel_id": parcel_id, "versions": [
        {"id": str(row.id), "geom": geom_to_geojson(row.geom), "captured_at": row.captured_at, "source": row.source}
        for row in rows
    ]}

@router.get("/{parcel_id}/comparison")
def comparison(parcel_id: str, db: Session = Depends(get_db)):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(404, "Parcel not found")
    row = db.execute(text("""
        SELECT ST_Area(p.geom::geography) AS current_area_sqm,
               ST_Area(v.geom::geography) AS historical_area_sqm,
               ST_Area(ST_SymDifference(p.geom, v.geom)::geography) AS boundary_difference_sqm,
               v.id AS historical_version_id, v.captured_at
        FROM parcels p LEFT JOIN LATERAL (
            SELECT * FROM parcel_versions WHERE parcel_id=p.id ORDER BY captured_at DESC LIMIT 1
        ) v ON true WHERE p.id=CAST(:id AS uuid)
    """), {"id": parcel_id}).mappings().one()
    result = dict(row)
    old, current = result["historical_area_sqm"], result["current_area_sqm"]
    result.update(parcel_id=parcel_id, area_difference_sqm=current-old if old is not None else None,
                  area_difference_percent=100*(current-old)/old if old else None,
                  method="PostGIS geodesic area; boundary difference is symmetric-difference area, not shift distance")
    return result

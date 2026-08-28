from backend.api.app.schemas.confidence import confidence_band
from backend.api.app.services.geo import geom_to_geojson
from backend.db.models.orm import Parcel


def parcel_to_out(p: Parcel) -> dict:
    return {
        "id": str(p.id),
        "project_id": str(p.project_id),
        "geom": geom_to_geojson(p.geom),
        "source": p.source,
        "status": p.status,
        "confidence_score": p.confidence_score,
        "confidence_band": confidence_band(p.confidence_score),
        "health_score": p.health_score,
        "land_use": p.land_use,
        "area_sqm": p.area_sqm,
        "version": p.version,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }

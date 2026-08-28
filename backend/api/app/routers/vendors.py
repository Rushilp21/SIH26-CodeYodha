from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.app.schemas.models import VendorOut, VendorServicesIn
from backend.db.models.orm import Vendor
from backend.db.session import get_db

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    rows = db.query(Vendor).all()
    return [
        VendorOut(id=str(v.id), name=v.name, services=v.services, contact_info=v.contact_info)
        for v in rows
    ]


@router.post("/{vendor_id}/services", response_model=VendorOut)
def update_services(vendor_id: str, body: VendorServicesIn, db: Session = Depends(get_db)):
    v = db.get(Vendor, vendor_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.services = body.services
    db.commit()
    db.refresh(v)
    return VendorOut(id=str(v.id), name=v.name, services=v.services, contact_info=v.contact_info)

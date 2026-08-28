from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal["created", "ingesting", "processing", "review", "completed"]
ParcelSource = Literal["ai_extracted", "existing_gis", "field_verified"]
ParcelStatus = Literal["ai_processed", "needs_review", "verified", "rejected"]
QueueStatus = Literal["pending", "assigned", "completed"]
ConfidenceBand = Literal["HIGH", "MEDIUM", "LOW"]
UserRole = Literal["surveyor", "gis_expert", "admin", "vendor"]
CorrectionType = Literal["boundary_adjust", "reject", "land_use_fix", "split", "merge"]


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class ProjectCreate(BaseModel):
    name: str
    area_of_interest: GeoJSONGeometry | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    area_of_interest: dict | None = None
    demo: bool = False


class ImageryUploadOut(BaseModel):
    project_id: str
    status: str
    message: str
    demo: bool = True


class ProcessOut(BaseModel):
    project_id: str
    status: str
    message: str
    demo: bool = True


class ProjectStatusOut(BaseModel):
    id: str
    name: str
    status: str
    parcel_count: int
    demo: bool = False


class ParcelOut(BaseModel):
    id: str
    project_id: str
    geom: dict
    source: str
    status: str
    confidence_score: float | None = None
    confidence_band: ConfidenceBand | None = None
    health_score: float | None = None
    land_use: str | None = None
    area_sqm: float | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ParcelPatch(BaseModel):
    geom: GeoJSONGeometry | None = None
    land_use: str | None = None
    status: ParcelStatus | None = None


class VerifyIn(BaseModel):
    geom: GeoJSONGeometry | None = None
    correction_type: CorrectionType = "boundary_adjust"
    notes: str | None = None


class VerifyOut(BaseModel):
    parcel_id: str
    status: str
    correction_id: str
    message: str


class EvidenceItem(BaseModel):
    component: str
    score: float
    explanation: str


class ExplanationOut(BaseModel):
    parcel_id: str
    explanation: str
    confidence_score: float | None = None
    health_score: float | None = None
    components: list[EvidenceItem]


class SurveyQueueItem(BaseModel):
    id: str
    parcel_id: str
    priority_score: float
    reason: str
    status: str
    assigned_to: str | None = None
    created_at: datetime | None = None


class AssignIn(BaseModel):
    assigned_to: str | None = None


class ChangeDetectionItem(BaseModel):
    parcel_id: str
    type: str
    magnitude: float
    detected_at: datetime | None = None
    demo: bool = True


class VendorOut(BaseModel):
    id: str
    name: str
    services: str
    contact_info: str | None = None


class VendorServicesIn(BaseModel):
    services: str


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    name: str
    email: str
    role: str

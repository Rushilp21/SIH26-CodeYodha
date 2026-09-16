from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from shapely.geometry import shape

ProjectStatus = Literal["created", "ingesting", "processing", "review", "completed"]
ParcelSource = Literal["ai_extracted", "existing_gis", "field_verified"]
ParcelStatus = Literal["ai_processed", "needs_review", "verified", "rejected"]
QueueStatus = Literal["pending", "assigned", "completed"]
ConfidenceBand = Literal["HIGH", "MEDIUM", "LOW"]
UserRole = Literal["surveyor", "gis_expert", "admin", "vendor"]
CorrectionType = Literal["boundary_adjust", "reject", "land_use_fix", "split", "merge"]
FalsePositiveLabel = Literal[
    "false_positive_building",
    "false_positive_road",
    "false_positive_canal",
    "false_positive_other",
]


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any

    @model_validator(mode="after")
    def valid_polygon(self):
        try:
            if self.type != "Polygon" or not isinstance(self.coordinates, list) or not self.coordinates:
                raise ValueError("A nonempty Polygon is required")
            for ring in self.coordinates:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Polygon rings must contain at least four positions and be closed")
                if any(not isinstance(point, (list, tuple)) or len(point) != 2 for point in ring):
                    raise ValueError("Polygon positions must be [longitude, latitude]")
            polygon = shape({"type": self.type, "coordinates": self.coordinates})
            if polygon.geom_type != "Polygon" or polygon.is_empty or not polygon.is_valid:
                raise ValueError("A valid, nonempty Polygon is required")
            for ring in [polygon.exterior, *polygon.interiors]:
                if any(not (-180 <= x <= 180 and -90 <= y <= 90) for x, y, *_ in ring.coords):
                    raise ValueError("Coordinates must use longitude/latitude EPSG:4326")
        except (TypeError, KeyError, IndexError) as exc:
            raise ValueError("Invalid Polygon coordinates") from exc
        return self


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
    evidence_parcel_count: int = 0
    rl_evidence_parcel_count: int = 0
    pipeline_provenance: str | None = None


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
    review_label: FalsePositiveLabel | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def label_requires_rejection(self):
        if self.review_label is not None and self.correction_type != "reject":
            raise ValueError("False-positive review labels require correction_type=reject")
        return self


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

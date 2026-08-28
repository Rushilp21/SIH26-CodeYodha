"""initial postgis schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("services", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_info", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("area_of_interest", Geometry(geometry_type="POLYGON", srid=4326), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "parcels",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("project_id", sa.Uuid(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("geom", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("land_use", sa.String(64), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_parcels_project_id", "parcels", ["project_id"])
    op.create_index("ix_parcels_status", "parcels", ["status"])
    op.execute("CREATE INDEX IF NOT EXISTS ix_parcels_geom ON parcels USING GIST (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_aoi ON projects USING GIST (area_of_interest)")

    op.create_table(
        "buildings",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("project_id", sa.Uuid(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=True),
        sa.Column("geom", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_buildings_project_id", "buildings", ["project_id"])
    op.create_index("ix_buildings_parcel_id", "buildings", ["parcel_id"])
    op.execute("CREATE INDEX IF NOT EXISTS ix_buildings_geom ON buildings USING GIST (geom)")

    op.create_table(
        "roads",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("project_id", sa.Uuid(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("geom", Geometry(geometry_type="LINESTRING", srid=4326), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_roads_project_id", "roads", ["project_id"])
    op.execute("CREATE INDEX IF NOT EXISTS ix_roads_geom ON roads USING GIST (geom)")

    op.create_table(
        "parcel_versions",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("geom", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
    )
    op.create_index("ix_parcel_versions_parcel_id", "parcel_versions", ["parcel_id"])

    op.create_table(
        "confidence_evidence",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_confidence_evidence_parcel_id", "confidence_evidence", ["parcel_id"])

    op.create_table(
        "corrections",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("surveyor_id", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("original_geom", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("corrected_geom", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("correction_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_corrections_parcel_id", "corrections", ["parcel_id"])

    op.create_table(
        "survey_queue",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("assigned_to", sa.Uuid(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_survey_queue_parcel_id", "survey_queue", ["parcel_id"])
    op.create_index("ix_survey_queue_status", "survey_queue", ["status"])

    op.create_table(
        "anomalies",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(as_uuid=False), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anomalies_parcel_id", "anomalies", ["parcel_id"])


def downgrade() -> None:
    op.drop_table("anomalies")
    op.drop_table("survey_queue")
    op.drop_table("corrections")
    op.drop_table("confidence_evidence")
    op.drop_table("parcel_versions")
    op.drop_table("roads")
    op.drop_table("buildings")
    op.drop_table("parcels")
    op.drop_table("projects")
    op.drop_table("vendors")
    op.drop_table("users")

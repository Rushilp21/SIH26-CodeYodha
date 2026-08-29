from uuid import uuid4

from geoalchemy2.elements import WKTElement

from backend.db.session import SessionLocal
from backend.db.models.orm import (
    User,
    Project,
    Parcel,
    ConfidenceEvidence,
    SurveyQueue,
    Vendor,
)


def seed():
    db = SessionLocal()

    try:
        # -------------------------
        # USERS
        # -------------------------
        users = [
            User(
                name="Admin User",
                email="admin@bhumisetu.in",
                role="admin",
            ),
            User(
                name="GIS Expert",
                email="gis@bhumisetu.in",
                role="gis_expert",
            ),
            User(
                name="Field Surveyor",
                email="surveyor@bhumisetu.in",
                role="surveyor",
            ),
        ]

        for user in users:
            if not db.query(User).filter(User.email == user.email).first():
                db.add(user)

        db.flush()

        # -------------------------
        # PROJECT
        # -------------------------
        project = db.query(Project).first()

        if not project:
            project = Project(
                name="Demo Urban Survey",
                status="review",
                area_of_interest=WKTElement(
                    "POLYGON((77.590 12.970, "
                    "77.600 12.970, "
                    "77.600 12.980, "
                    "77.590 12.980, "
                    "77.590 12.970))",
                    srid=4326,
                ),
            )
            db.add(project)
            db.flush()

        # -------------------------
        # PARCELS
        # -------------------------
        if db.query(Parcel).filter(Parcel.project_id == project.id).count() == 0:

            parcel_data = [
                (
                    "0.94",
                    "HIGH",
                    "residential",
                    "POLYGON((77.592 12.972, 77.594 12.972, 77.594 12.974, 77.592 12.974, 77.592 12.972))",
                    420.0,
                    92.0,
                ),
                (
                    "0.76",
                    "MEDIUM",
                    "commercial",
                    "POLYGON((77.595 12.973, 77.598 12.973, 77.598 12.976, 77.595 12.976, 77.595 12.973))",
                    760.0,
                    68.0,
                ),
                (
                    "0.42",
                    "LOW",
                    "mixed",
                    "POLYGON((77.592 12.976, 77.596 12.976, 77.596 12.979, 77.592 12.979, 77.592 12.976))",
                    1100.0,
                    41.0,
                ),
            ]

            for confidence, band, land_use, polygon, area, health in parcel_data:

                score = float(confidence)

                parcel = Parcel(
                    id=str(uuid4()),
                    project_id=project.id,
                    geom=WKTElement(polygon, srid=4326),
                    source="ai_extracted",
                    status="needs_review",
                    confidence_score=score,
                    health_score=health,
                    land_use=land_use,
                    area_sqm=area,
                    version=1,
                )

                db.add(parcel)
                db.flush()

                # Evidence used by /explanation
                db.add_all(
                    [
                        ConfidenceEvidence(
                            parcel_id=parcel.id,
                            component="boundary",
                            score=score,
                            explanation=f"AI boundary confidence: {score:.2f}",
                        ),
                        ConfidenceEvidence(
                            parcel_id=parcel.id,
                            component="building",
                            score=min(score + 0.03, 1.0),
                            explanation="Building footprint alignment detected from imagery.",
                        ),
                        ConfidenceEvidence(
                            parcel_id=parcel.id,
                            component="topology",
                            score=min(score + 0.01, 1.0),
                            explanation="Parcel topology passed automated validation.",
                        ),
                    ]
                )

                # Low confidence → survey queue
                if score < 0.60:
                    db.add(
                        SurveyQueue(
                            parcel_id=parcel.id,
                            priority_score=100 - health,
                            reason="Low AI confidence; field verification recommended.",
                            status="pending",
                        )
                    )

        # -------------------------
        # VENDOR
        # -------------------------
        if db.query(Vendor).count() == 0:
            db.add(
                Vendor(
                    name="GeoSurvey Solutions",
                    services="Drone Survey, GNSS Survey, Ground Truthing",
                    contact_info="survey@demo.in",
                )
            )

        db.commit()

        print("================================")
        print("BhumiSetu demo data seeded")
        print("================================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()
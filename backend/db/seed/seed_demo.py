"""Seed demo data for tomorrow's walkthrough. DEMO / mock — not live ML output.

Run from repo root with PYTHONPATH=repo root:

    python backend/db/seed/seed_demo.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from geoalchemy2.elements import WKTElement
from shapely.geometry import Polygon, box, mapping
from sqlalchemy import text

from backend.db.models.orm import (
    Anomaly,
    Building,
    ConfidenceEvidence,
    Correction,
    Parcel,
    ParcelVersion,
    Project,
    Road,
    SurveyQueue,
    User,
    Vendor,
)
from backend.db.session import SessionLocal, engine

DEMO_PROJECT_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
# Ranchi, Jharkhand — small valid rectangles in EPSG:4326
ORIGIN_LON = 85.3096
ORIGIN_LAT = 23.3441


def rect(col: int, row: int, w: float = 0.00055, h: float = 0.00042, gap: float = 0.00008) -> Polygon:
    minx = ORIGIN_LON + col * (w + gap)
    miny = ORIGIN_LAT + row * (h + gap)
    poly = box(minx, miny, minx + w, miny + h)
    assert poly.is_valid and poly.area > 0
    return poly


def wkt_poly(poly: Polygon) -> WKTElement:
    return WKTElement(poly.wkt, srid=4326)


def evidence(parcel_id: str, scores: dict[str, float], extra: str) -> list[ConfidenceEvidence]:
    texts = {
        "segmentation": f"Segmentation raw confidence {scores['segmentation']:.2f}.",
        "topology": "Topology remained valid." if scores["topology"] >= 0.8 else "Topology flags present.",
        "edge_alignment": f"Edge alignment score {scores['edge_alignment']:.2f}.",
        "deviation_from_baseline": extra,
    }
    return [
        ConfidenceEvidence(
            id=str(uuid4()),
            parcel_id=parcel_id,
            component=k,
            score=v,
            explanation=texts[k],
        )
        for k, v in scores.items()
    ]


def seed() -> None:
    # Import cadastral-intelligence by file path is forbidden across owners at runtime
    # in production; seed uses inline health numbers matching Dev 3's frozen formula.
    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        db.commit()
    except Exception:
        db.rollback()

    # Never clear a user's database to load demonstration fixtures.
    if db.query(Project).first() or db.query(User).first() or db.query(Vendor).first():
        db.close()
        raise RuntimeError("Demo seeding requires an empty database. Existing records were preserved.")

    users = [
        User(id=str(uuid4()), name="Asha Surveyor", email="surveyor@bhumisetu.demo", role="surveyor"),
        User(id=str(uuid4()), name="Rahul GIS", email="gis@bhumisetu.demo", role="gis_expert"),
        User(id=str(uuid4()), name="Meera Admin", email="admin@bhumisetu.demo", role="admin"),
        User(id=str(uuid4()), name="Kiran Vendor", email="vendor@bhumisetu.demo", role="vendor"),
    ]
    db.add_all(users)

    vendor = Vendor(
        id=str(uuid4()),
        name="CodeYodha Field Services",
        services="GNSS, cadastral resurvey, drone RGB",
        contact_info="vendor@bhumisetu.demo",
    )
    db.add(vendor)

    aoi = box(ORIGIN_LON - 0.001, ORIGIN_LAT - 0.001, ORIGIN_LON + 0.005, ORIGIN_LAT + 0.004)
    project = Project(
        id=DEMO_PROJECT_ID,
        name="DEMO Ranchi Ward-12 Cadastral Review",
        area_of_interest=wkt_poly(aoi),
        status="review",
    )
    db.add(project)
    db.flush()

    specs = [
        # col, row, conf, health, status, source, land_use, queue?, anomaly?
        (0, 0, 0.92, 0.88, "verified", "field_verified", "residential", False, None),
        (1, 0, 0.90, 0.86, "ai_processed", "ai_extracted", "residential", False, None),
        (2, 0, 0.88, 0.84, "ai_processed", "ai_extracted", "commercial", False, None),
        (3, 0, 0.86, 0.81, "ai_processed", "existing_gis", "residential", False, None),
        (0, 1, 0.78, 0.72, "needs_review", "ai_extracted", "residential", True, None),
        (1, 1, 0.71, 0.68, "needs_review", "ai_extracted", "agriculture", True, "boundary_shift"),
        (2, 1, 0.65, 0.61, "needs_review", "ai_extracted", "residential", True, None),
        (3, 1, 0.62, 0.58, "needs_review", "existing_gis", "vacant", True, "overlap"),
        (0, 2, 0.54, 0.49, "needs_review", "ai_extracted", "residential", True, "encroachment"),
        (1, 2, 0.48, 0.44, "needs_review", "ai_extracted", "industrial", True, None),
        (2, 2, 0.41, 0.39, "needs_review", "ai_extracted", "agriculture", True, "topology_break"),
        (3, 2, 0.35, 0.33, "needs_review", "ai_extracted", "residential", True, None),
        (0, 3, 0.91, 0.87, "ai_processed", "ai_extracted", "public", False, None),
        (1, 3, 0.73, 0.70, "needs_review", "ai_extracted", "residential", True, None),
        (2, 3, 0.67, 0.63, "needs_review", "existing_gis", "commercial", True, None),
        (3, 3, 0.58, 0.52, "needs_review", "ai_extracted", "residential", True, None),
    ]

    now = datetime.now(timezone.utc)
    first_low_id = None
    verified_id = None

    for i, (c, r, conf, health, status, source, land_use, queued, anom) in enumerate(specs):
        poly = rect(c, r)
        pid = str(uuid4())
        if status == "verified":
            verified_id = pid
        if conf < 0.60 and first_low_id is None:
            first_low_id = pid
        area_sqm = poly.area * (111_000**2) * 0.85  # rough demo area, not a CRS-correct geodesic
        p = Parcel(
            id=pid,
            project_id=DEMO_PROJECT_ID,
            geom=wkt_poly(poly),
            source=source,
            status=status,
            confidence_score=conf,
            health_score=health,
            land_use=land_use,
            area_sqm=round(area_sqm, 1),
            version=2 if status == "verified" else 1,
        )
        db.add(p)
        db.flush()

        extra = (
            "Boundary shifted 2.3m NE relative to the baseline; "
            "edge alignment improved while topology remained valid."
            if i == 5
            else f"Deviation from baseline component {max(0.0, 1 - abs(0.8 - conf)):.2f}."
        )
        scores = {
            "segmentation": min(1.0, conf + 0.02),
            "topology": 0.95 if anom != "topology_break" else 0.42,
            "edge_alignment": min(1.0, conf + 0.05),
            "deviation_from_baseline": max(0.2, conf - 0.1),
        }
        db.add_all(evidence(pid, scores, extra))

        if queued:
            db.add(
                SurveyQueue(
                    id=str(uuid4()),
                    parcel_id=pid,
                    priority_score=round(1.0 - conf, 3),
                    reason="LOW confidence — field verification" if conf < 0.60 else "MEDIUM confidence — GIS review",
                    status="pending",
                )
            )
        if anom:
            db.add(
                Anomaly(
                    id=str(uuid4()),
                    parcel_id=pid,
                    type=anom,
                    magnitude=round(1.2 + i * 0.15, 2),
                    detected_at=now - timedelta(days=2),
                )
            )

        if i == 0:
            older = rect(c, r)
            older = box(older.bounds[0] - 0.00004, older.bounds[1], older.bounds[2], older.bounds[3])
            db.add(
                ParcelVersion(
                    id=str(uuid4()),
                    parcel_id=pid,
                    geom=wkt_poly(older),
                    captured_at=now - timedelta(days=400),
                    source="existing_gis",
                )
            )
            db.add(
                ParcelVersion(
                    id=str(uuid4()),
                    parcel_id=pid,
                    geom=wkt_poly(poly),
                    captured_at=now,
                    source="field_verified",
                )
            )

        if i < 4:
            minx, miny, maxx, maxy = poly.bounds
            bldg = box(minx + 0.00008, miny + 0.00008, maxx - 0.00008, maxy - 0.00008)
            db.add(
                Building(
                    id=str(uuid4()),
                    project_id=DEMO_PROJECT_ID,
                    parcel_id=pid,
                    geom=wkt_poly(bldg),
                    confidence_score=0.81,
                )
            )

    road = Road(
        id=str(uuid4()),
        project_id=DEMO_PROJECT_ID,
        geom=WKTElement(
            f"LINESTRING({ORIGIN_LON} {ORIGIN_LAT}, {ORIGIN_LON + 0.0025} {ORIGIN_LAT + 0.0002})",
            srid=4326,
        ),
        confidence_score=0.77,
    )
    db.add(road)
    db.commit()
    print("Seeded DEMO project", DEMO_PROJECT_ID)
    print("Login emails: gis@bhumisetu.demo / surveyor@bhumisetu.demo / admin@bhumisetu.demo  password: demo")
    print("Verified parcel:", verified_id)
    print("Example low-confidence parcel:", first_low_id)


if __name__ == "__main__":
    seed()

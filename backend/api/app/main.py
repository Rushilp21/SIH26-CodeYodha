from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from backend.db.session import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError
from fastapi.responses import JSONResponse

from backend.api.app.routers import (
    auth,
    change_detection,
    imagery,
    parcels,
    parcel_history,
    parcel_import,
    projects,
    survey_queue,
    vendors,
)

app = FastAPI(title="BhumiSetu API", version="0.1.0")

@app.exception_handler(OperationalError)
@app.exception_handler(ProgrammingError)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable or schema not initialized. Start PostGIS and run the database migrations."})

@app.exception_handler(DataError)
async def invalid_database_value(request, exc):
    return JSONResponse(status_code=422, content={"detail": "Invalid identifier or value. Use the parcel, project and user IDs returned by this API."})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(imagery.router)
app.include_router(parcels.router)
app.include_router(parcel_history.router)
app.include_router(parcel_import.router)
app.include_router(survey_queue.router)
app.include_router(change_detection.router)
app.include_router(vendors.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bhumisetu-api"}

@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "postgresql",
        }
    except Exception as exc:
        return {
            "status": "error",
            "database": "postgresql",
            "detail": str(exc),
        }
        
@app.get("/health/postgis")
def postgis_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("SELECT PostGIS_Version()")
        ).scalar()

        return {
            "status": "ok",
            "postgis_version": result,
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }

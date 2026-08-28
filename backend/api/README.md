# FastAPI (Developer 4)

## Purpose
HTTP API for Web-GIS and admin-vendor. Orchestrates jobs. Owns auth and DB access.

## Owner
Developer 4. Do not import Dev 1/2/3 implementation packages.

## Inputs
JSON requests (EPSG:4326 geometries). Env from `.env`.

## Outputs
JSON matching `shared-schemas/api/`. Swagger at `/docs`.

## Dependencies
Postgres+PostGIS, Redis (optional for Celery). Seeded data for demo.

## Run (from repo root)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/api/requirements.txt
copy .env.example .env
set PYTHONPATH=%CD%
uvicorn backend.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: GET http://localhost:8000/health
Docs: http://localhost:8000/docs

Demo login: `gis@bhumisetu.demo` / `demo`

## Tests

```
pytest backend/api/tests
```

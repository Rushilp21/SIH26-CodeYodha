# Run the canonical GIS

Reference design: `D:/ParcelAI-UI`. Application: `D:/SIH/frontend/web-gis`.
React 18, TypeScript and MapLibre are preserved. No ML source was replaced.

## Startup

`ECONNREFUSED 127.0.0.1:8000` in Vite means the API is not listening;
restarting `npm run dev` will not start it. The proxy now returns an explanatory
503 instead of an empty 500 when the API is unreachable.

In Git Bash, after Docker Desktop reports its engine is running:

```bash
cd /d/SIH
docker compose up -d --build
docker compose ps -a
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

The `migrate` container should exit with code 0; API/PostGIS should be running.
If startup fails, inspect `docker compose logs --tail=100 api migrate postgres`.
Do not run a separate Uvicorn server on port 8000 while using the Compose API.

In a second terminal:

```bash
cd /d/SIH/frontend/web-gis
npm run dev
```

Keep Docker running while using the application. Refresh the browser after the
health checks succeed. An empty project list is normal for an empty database;
use the dashboard import workflow below. Imported data alone does not supply
historical surveys, anomaly events or completed RL results.

1. Start Docker Desktop successfully. From `D:/SIH`, run `docker compose up -d --build`.
   Compose starts PostGIS, Redis, migrations, API and the existing Celery worker.
   It preserves the database volume and does not seed or reset data.
2. From `D:/SIH/frontend/web-gis`, run `npm install` if dependencies are missing,
   then `npm run dev`. Open the URL Vite prints.
3. The default `/api` proxy targets `http://127.0.0.1:8000`. A custom
   `VITE_API_BASE_URL` overrides it. Production hosting must proxy `/api` to the API
   or configure an explicit base URL with appropriate backend CORS settings.
4. On the dashboard, create/import a project using
   `D:/SIH/data/raw/segmentation/parcels_simplified.geojson` (15 validated parcels).
   Alternatively open an existing project. Imports require an empty project to
   prevent accidental duplication/overwrite. Mixed-class segmentation files are rejected.

The import is an existing output, not a fresh inference run. Raw segmentation
confidence is not promoted to boundary confidence, health score or RL completion.

## Current machine blocker

Docker Desktop startup log reports a crash initializing its `dockerInference`
socket: "The file cannot be accessed by the system". The Linux engine does not
become usable, so PostGIS/Compose cannot start. No Docker reset or deletion was
performed. Repair Docker Desktop, or configure DATABASE_URL to an accessible
PostGIS database and run `alembic -c backend/db/alembic.ini upgrade head`.

A local `.venv` was created and API dependencies plus httpx installed for tests.
For a non-Docker API, run `.venv/Scripts/python.exe -m uvicorn backend.api.app.main:app
--host 127.0.0.1 --port 8000` from the root (one line), with a working database.

## Implemented and verified separately

- Dashboard/project chooser, map panels and parcel filters, review/verify/reject,
  explicit GeoJSON editing, stored history and old/current comparison, analytics
  distributions and downloadable JSON reports.
- Same-origin frontend proxy and useful database/service errors.
- History and comparison read APIs; imports; geometry validation; preserved old
  versions and recomputed geodesic areas; stale confidence invalidation on edits.
- Demo seeding now refuses populated databases; no demo data was loaded.
- TypeScript/Vite production build and frontend provenance tests pass.
- Backend contract tests pass; the API imports and serves health successfully.
- Live proxy requests reach the API; database requests report HTTP 503 correctly.

## Not yet complete

- Full PostGIS-backed end-to-end import/edit/history verification is blocked by Docker.
- Segmentation inference is a NotImplementedError stub. Trained RL policy weights
  are missing. Imagery/process endpoints return HTTP 501 rather than fake success.
- Model accuracy/mIoU trends, anomaly-resolution history, imagery/DSM layers and
  evidence uploads have no working source API; they are not silently fabricated.
- Existing demo authentication is not a production security implementation.

Tests: `node --test tests/change-detection.cjs tests/data-provenance.cjs` from the
frontend; `.venv/Scripts/python.exe -m unittest discover -s backend/api/tests -v`
from the root. The MapLibre bundle-size warning is nonfatal.

See `frontend/web-gis/MOCK_TO_API_MAPPING.md` for the mock-to-real-data audit.

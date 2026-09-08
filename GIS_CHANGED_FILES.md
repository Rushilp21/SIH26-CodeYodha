# Changed files — cumulative GIS integration

This is the working-tree inventory for the requested UI stages and API fixes. No commits or repository merges were made. ML source files were not replaced.

- `M backend/api/app/main.py`
- `M backend/api/app/routers/change_detection.py`
- `M backend/api/app/routers/parcels.py`
- `M backend/api/app/routers/projects.py`
- `M backend/api/app/routers/survey_queue.py`
- `M backend/api/app/schemas/models.py`
- `M backend/api/app/tasks/celery_app.py`
- `M backend/db/seed/seed_demo.py`
- `M backend/db/session.py`
- `M docker-compose.yml`
- `M frontend/shared/types/index.ts`
- `M frontend/web-gis/src/App.tsx`
- `M frontend/web-gis/src/api/client.ts`
- `M frontend/web-gis/src/components/AppShell.tsx`
- `D frontend/web-gis/src/data/dashboardAdapter.ts`
- `M frontend/web-gis/src/hooks/useAsync.ts`
- `M frontend/web-gis/src/index.css`
- `M frontend/web-gis/src/map/ParcelMap.tsx`
- `M frontend/web-gis/src/pages/DashboardPage.tsx`
- `M frontend/web-gis/src/pages/ParcelDetailPage.tsx`
- `M frontend/web-gis/src/pages/ProjectPage.tsx`
- `M frontend/web-gis/src/pages/ReviewQueuePage.tsx`
- `M frontend/web-gis/vite.config.ts`
- `?? RUN_WEB_GIS.md`
- `?? backend/api/app/routers/parcel_history.py`
- `?? backend/api/app/routers/parcel_import.py`
- `?? backend/api/tests/test_gis_contracts.py`
- `?? frontend/web-gis/MOCK_TO_API_MAPPING.md`
- `?? frontend/web-gis/src/components/BackendStatus.tsx`
- `?? frontend/web-gis/src/components/ImportWorkspace.tsx`
- `?? frontend/web-gis/src/components/ParcelDetailsPanel.tsx`
- `?? frontend/web-gis/src/components/ProcessingPanel.tsx`
- `?? frontend/web-gis/src/data/changeDetection.ts`
- `?? frontend/web-gis/src/data/dashboardMetrics.ts`
- `?? frontend/web-gis/src/pages/AnalyticsPage.tsx`
- `?? frontend/web-gis/src/pages/ChangeDetectionPage.tsx`
- `?? frontend/web-gis/src/styles/analytics.css`
- `?? frontend/web-gis/src/styles/change-detection.css`
- `?? frontend/web-gis/tests/change-detection.cjs`
- `?? frontend/web-gis/tests/data-provenance.cjs`
- `?? infra/docker/Dockerfile.api`
- `?? GIS_CHANGED_FILES.md` (this inventory)

See RUN_WEB_GIS.md for startup, verification and remaining blockers; frontend/web-gis/MOCK_TO_API_MAPPING.md for data provenance.


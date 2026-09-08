# ParcelAI reference data audit and integration contract

Scope: reference `D:/ParcelAI-UI/src`; canonical UI `D:/SIH/frontend/web-gis`.
The reference remains unchanged. This inventory covers all reference business-data
literals and generated data families; colors, icon paths, spacing, animation timing,
chart dimensions and other presentation constants are not business data.

## Required values

| Reference mock | Real target field / endpoint | Final display rule |
| --- | --- | --- |
| `dashboardStats.totalParcels = 1248` | `GET /projects`, then `GET /parcels?project_id={id}`; count returned records | Total parcels, not necessarily parcels processed by ML. |
| `autoApproved = 847`, `autoApprovedPct = 67.9` | No auto-approval outcome field. `Parcel.status === verified` supplies a different, valid count. | Display **Verified**; never label high confidence or verified records as auto-approved. |
| `pendingReview = 312` | Count parcels whose `status === needs_review` | Needs review. Do not use queue length as a substitute. |
| `fieldVerification = 89` | `GET /survey-queue?project_id={id}`; unique `parcel_id` for `status` pending/assigned | Pending field surveys. Field completion instead uses parcel `source === field_verified` / status verified. Queue status alone does not prove field completion. |
| `avgConfidence = 78.4` | Mean of non-null `Parcel.confidence_score`, multiplied by 100 | Stored boundary confidence; not accuracy, IoU, or proof of RL execution. No samples: n/a. |
| `P-0100` through `P-0147`; activity/change IDs such as `P-0203`, `P-0182`, `P-0098` | `Parcel.id`, `ChangeDetectionItem.parcel_id`, `SurveyQueueItem.parcel_id` | Preserve backend UUIDs for lookup/navigation; truncation only for display. No fabricated fallback IDs. |
| Survey history: 2022/2023/2024/2026; fabricated area offsets | `GET /parcels/{id}/history`: versions[].geom/captured_at/source; `GET /parcels/{id}/comparison`: historical_area_sqm, area_difference_sqm, area_difference_percent, boundary_difference_sqm | Show stored versions and geodesic measurements. No history means unavailable; source labels distinguish edits from surveys. |
| `FLAG_REASONS`, generated `flags`, eight `changeEvents` | `GET /change-detection?project_id={id}` → type/magnitude/detected_at; `GET /parcels/{id}/explanation` → explanation/components | Render only returned event types and evidence. No invented anomalies on an empty or failed request. |
| `SEED`, `makePolygon`, `polygon`, `lat`, `lng` arrays | `GET /parcels?project_id={id}` → geom, GeoJSON EPSG:4326 | Use canonical MapLibre GeoJSON `[longitude, latitude]`; never port reference `[latitude, longitude]` arrays. Fit bounds from actual geometry. |

## All other reference data families

| Location / mock value | Target mapping | Availability and policy |
| --- | --- | --- |
| `mockData.js`: CITY_CENTER `[18.5204,73.8567]` | Bounds of returned `Parcel.geom` | Reference Pune center removed. Existing basemap is context, not drone imagery or pipeline output. |
| CONF_SEED 94,71,88,…; random 38–98 | Parcel.confidence_score / confidence_band | Convert 0..1 to percentage for display; null stays unavailable. |
| Confidence thresholds 85/62; generated approved/review/field | Shared target thresholds HIGH >= .85, MEDIUM >= .60; Parcel.status | The reference's .62 threshold is incompatible. Eligibility is not approval. |
| Priority High/Medium/Low from confidence <55/<75 | SurveyQueueItem.priority_score and reason | Show numeric backend priority. No arbitrary severity bands. |
| Area formula `120 + ((i*47+13)%2280)` | Parcel.area_sqm | Stored area, not a newly calculated area or area difference. |
| LAND_USE rotation | Parcel.land_use | Missing land use remains unavailable. |
| WARDS: Shivajinagar/Kothrud/Hadapsar/Aundh/Baner/Yerawada/Wanowrie | No ward field | Omit / unavailable, not inferred from coordinates. |
| ZONES North/South/East/West/Central | No zone field | Omit / unavailable. |
| `Owner ${id}` | No owner field | Omit / unavailable. |
| `SN-${1000+i*17}` | No survey-number field | Omit / unavailable. |
| Last-updated dates 2026-08-01…24 | Parcel.updated_at | Record timestamp only. |
| Model corrections 34 (Aug) | POST /parcels/{id}/verify returns correction_id; no correction-list/aggregate route | Historical correction counts unavailable. A write response does not establish retraining. |
| Processing timeline Jan…Aug: 42,78,115,203,287,341,398,312 | No processing-history API | Do not port; created_at would mean record creation, not inference completion. |
| Confidence histogram counts 12,28,67,134,421,489,97 | Can bin returned Parcel.confidence_score | Reference series not imported. Use only real samples if chart added. |
| Land-use chart counts 412,187,94,68,231,145,111 | Can group Parcel.land_use | Reference series not imported. |
| Anomalies by zone: 23/18,31/25,17/11,28/20,42/31 detected/resolved | Event type/count is available; zones and resolution state are not | No resolved-by-zone chart. |
| Accuracy Mar…Aug: 71.2,74.8,78.1,80.3,83.7,86.2 | No evaluation-metrics API | Unavailable; do not substitute confidence. |
| mIoU Mar…Aug: .64,.67,.71,.74,.78,.81 | No evaluation-metrics API | Unavailable. |
| Turnaround Wk1…8: 4.2,3.8,3.1,2.7,2.4,2.9,2.1,1.8 days | No review lifecycle API | Unavailable. |
| Recent activity eight entries; officer Sharma; 2/8/15/32 min, 1/3/5 hr ago; batches of 18, 12 corrections | No activity-feed API | Removed even the target's labelled demo adapter; display unavailable. |
| CD-001…CD-008 IDs | Change endpoint has no event ID | Use a local composite render key, never present it as a backend ID. |
| Event categories New Construction/Demolition/Boundary Shift/Land-Use Change | ChangeDetectionItem.type | Dynamic categories; engine currently emits boundary_shift, topology_break, encroachment etc. Never translate boundary_shift into confirmed construction/demolition. |
| Event descriptions and >2m shift | Explanation.explanation/components | No per-event explanation in change response. Show parcel evidence as parcel evidence; do not invent event causality or physical distances. |
| Event dates Aug 10/12/14/15/17/18/20/22 | ChangeDetectionItem.detected_at | Actual timestamp only. |
| Event affected areas 340,180,620,890,510,95,2100,1240 m² | No affected-area field | Unavailable. Magnitude is not m², metres, or a universally comparable severity score. |
| Event severity High/Medium/Low | No severity field | Display magnitude and survey priority separately; do not synthesize severity. |
| Event lat/lng arrays | Join event.parcel_id to Parcel.geom | Missing join: geometry unavailable. |
| FLAG_REASONS OVERLAP/FOOTPRINT/AREA_CHANGE/SPLIT/ROAD_ENCROACH/MISSING/LOW_CONF/DUPLICATE; >15% and >80% claims | Actual anomaly types + explanation components + survey queue reason | Each string is only a design example; no deterministic substitution. Typed topology_break/overlap events can identify reported topology anomalies; regex on narrative cannot (e.g. “no overlaps”). |

## Hardcoded values outside mockData.js

| Reference component | Mock behavior/value | Target mapping / handling |
| --- | --- | --- |
| Dashboard PipelineBar | Ingested 100%, Segmented 96%, RL Refined 91%, Validated 84%, Ready 78% | GET /projects/{id}/status → status; POST /projects/{id}/process → message/demo; GET /projects/{id}/task/{taskId} → state/result. No per-stage percentages. |
| Dashboard cards and copy | +312 this month, +4.1% accuracy/confidence, 34 corrections | No trend endpoints; omitted. |
| Shell | Model v2.4 / always Live | No model-version endpoint. API health uses GET /health; this does not mean ML/RL is running. |
| Map/Review pipeline widget | Status-based Ingested/Segmented/RL Refined/Validated/Ready labels | Only show recorded source/status and actual evidence. Mere presence of components does not prove RL ran. |
| Map/Review confidence copy | “Auto-approved by AI pipeline” | No auto-approval provenance field; removed. |
| Map LAYERS | Drone/orthorectified imagery, footprints, roads, land use, DSM/DTM toggles | No imagery/footprint/road/DSM read API. Only actual parcel source toggles are enabled. Basemap is explicitly contextual. |
| Map editor | Shoelace area ×111320²; local edited polygons | GeoJSON preview/editor uses PATCH /parcels/{id}. Backend validates polygons, archives previous geometry and calculates geodesic area. Old confidence evidence is invalidated. No nudge or degree-based area remains. |
| ParcelContext approve | Local approved status, confidence inflated to >=85, Aug 29 date | POST /parcels/{id}/verify records correction, sets verified/source/version. Refetch parcel; never inflate confidence or assign timestamps locally. |
| ParcelContext reject | Local field status / High priority / Aug29 date | POST /parcels/{id}/verify with correction_type=reject now records rejection and completes active survey entries. It does not fabricate a new field assignment or notes. |
| ParcelContext ground truth | Immediate approved state and success flash | Existing verify endpoint saves a boundary correction. No evidence-upload API; do not claim an upload happened. |
| ChangeDetection | 2024 Survey / 2026 AI Scan badges | Historical map uses versions[].geom/captured_at/source; current map uses Parcel.geom/version. Matching initial bounds and measured comparison metrics replace fixed year labels. |
| ChangeDetection buttons | Review Parcel / Mark Resolved have no handlers | Review links to real parcel route; no resolve endpoint, no fake success control. |
| Analytics KPIs | .81 mIoU (+.03); 86.2% accuracy (+2.5%); 1.8 days (-2.4); 105/141 (74%) resolved | These evaluation metrics are unavailable. Analytics instead displays real parcel counts, average stored confidence/health and distributions of land use, review status, confidence bands and queue status. |
| Analytics exports | Fixed report timestamp; inert PDF/GeoJSON/CSV buttons | Working JSON report exports the API records used by the charts, project demo flags and actual client export time. No server report-generation claim. |
| Login | officer@pmcgis.gov.in, masked dummy password, 1200ms automatic success | POST /auth/login and GET /auth/me exist but are demo auth. Reference simulated login is not ported. |
| Login copy | Pune municipal portal / monitored sessions / remembered login / forgot password | No supporting target workflow; not ported. Static project branding is not authentication or monitoring evidence. |
| Shell notifications/profile/logout | Decorative buttons / local auth toggle | Unavailable controls are disabled or absent; no apparent working control with silent no-op. |

## Backend output contract and remaining integration work

The UI consumes stored polygons, confidence, health, land use, source/status/version,
explanation components, anomaly magnitudes, and survey priorities through the existing API.
It does not substitute reference arrays. The dashboard imports user-selected parcel
GeoJSON through POST /projects/{id}/parcels/import into an empty project. The source
files data/raw/segmentation/parcels_simplified.geojson and parcels_only.geojson each
contain 15 parcels. Imported raw_confidence is stored as segmentation evidence,
not fabricated boundary confidence, health score or completed RL status.

Verified against `backend/api/app/tasks/pipeline.py`: the current Celery worker has
TODOs for ingestion, segmentation, RL refinement, DB writes and project-status updates.
The task scaffold returns `{status: "review", demo: true, ml: false}`. To prevent
misleading state changes, process and imagery routes now return explicit HTTP 501
until a real orchestrator is implemented. No fake job is queued. The client retains
task-status support for future backend integration. Segmentation inference raises
NotImplementedError; trained RL policy files are absent from the models folder.

`GET /change-detection` and `/projects` derive demo from
the project name. These signals are displayed; demo=false is not proof that a record
was produced by a trained model. Per-record run provenance is not supplied.

Remaining backend work:

1. Wire the existing worker to actual ingestion/segmentation/RL, persist outputs and update status.
2. Return structured task_id, stage progress, model/run identity and provenance.
3. Persist model evaluation and run provenance; history and measured geometry comparison endpoints are now implemented.
4. Expose correction/activity history, evaluation metrics and anomaly-resolution workflows if needed.

Until then, missing data is labelled unavailable; no pending queue, source tag, task
success, confidence score, or stored evidence is promoted into a completed-RL claim.

import type { Explanation, Parcel, Project, SurveyQueueItem } from "@shared/types";

export type DashboardSnapshot = {
  projects: Project[];
  parcels: Parcel[];
  queue: SurveyQueueItem[];
};

export type ProcessResponse = { project_id: string; status: string; message: string; demo: boolean; task_id?: string };
export type ProcessingTask = { project_id: string; task_id: string; state: string; result: unknown };
export type FalsePositiveLabel = "false_positive_building" | "false_positive_road" | "false_positive_canal" | "false_positive_other";
export type ReviewLabelExport = {
  schema_version: "bhumisetu.review-labels.v1";
  type: "FeatureCollection";
  name: string;
  generated_at: string;
  project: { id: string; name: string };
  summary: {
    project_parcels: number;
    eligible_reviewed_labels: number;
    positive_boundaries: number;
    hard_negatives: number;
    false_positive_classes: Record<string, number>;
    rejected_without_specific_label: number;
    unreviewed_or_ineligible: number;
    recommended_minimum: { total: number; positive_boundaries: number; hard_negatives: number };
    training_ready: boolean;
  };
  features: Array<{ type: "Feature"; geometry: Parcel["geom"]; properties: Record<string, unknown> }>;
};

export function fetchHealth(): Promise<{ status: string; service: string }> {
  return getJson("/health");
}

export function fetchProcessingTask(projectId: string, taskId: string): Promise<ProcessingTask> {
  return getJson(`/projects/${encodeURIComponent(projectId)}/task/${encodeURIComponent(taskId)}`);
}

export type ChangeDetectionItem = {
  parcel_id: string;
  type: string;
  magnitude: number;
  detected_at: string | null;
  demo: boolean;
};

export type ReviewWorkspace = {
  parcels: Parcel[];
  queue: SurveyQueueItem[];
  changes: ChangeDetectionItem[];
  explanations: Record<string, Explanation | null>;
};

const BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try { res = await fetch(`${BASE}${path}`, { ...init, signal: AbortSignal.timeout(20000) }); }
  catch { throw new Error("API connection failed. Check that the API and database are running on port 8000."); }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string"
      ? detail
      : typeof detail?.message === "string"
        ? detail.message
        : null;
    throw new Error(message ?? `API ${res.status} (${path}). Check backend service logs.`);
  }
  return res;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await request(path);
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  return getJson("/projects");
}

export async function createProject(name: string): Promise<Project> {
  return (await request("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) })).json();
}
export async function importParcelFile(id: string, collection: unknown): Promise<{ imported: number }> {
  return (await request(`/projects/${id}/parcels/import`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(collection) })).json();
}
export async function importPipelineParcelFile(id: string, parcels: unknown[], geojson?: unknown): Promise<{ imported: number }> {
  return (await request(`/projects/${id}/parcels/pipeline-import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parcels, ...(geojson ? { geojson } : {}) }),
  })).json();
}

/** Aggregates only existing canonical endpoints; no mock parcel metrics are used. */
export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const projects = await fetchProjects();
  const [parcelGroups, queueGroups] = await Promise.all([
    Promise.all(projects.map((project) => fetchParcels(project.id))),
    Promise.all(projects.map((project) => fetchQueue(project.id))),
  ]);
  return { projects, parcels: parcelGroups.flat(), queue: queueGroups.flat() };
}

export async function fetchProjectStatus(id: string) {
  return getJson<{ id: string; name: string; status: string; parcel_count: number; demo: boolean; evidence_parcel_count: number; rl_evidence_parcel_count: number; pipeline_provenance: string | null }>(
    `/projects/${id}/status`
  );
}

export function fetchReviewLabelExport(projectId: string): Promise<ReviewLabelExport> {
  return getJson(`/projects/${encodeURIComponent(projectId)}/review-labels/export`);
}

export async function processProject(id: string): Promise<ProcessResponse> {
  const res = await request(`/projects/${id}/process`, { method: "POST" });
  if (!res.ok) throw new Error("process failed");
  return res.json();
}

export async function uploadImagery(id: string): Promise<ProcessResponse> {
  const res = await request(`/projects/${id}/imagery`, { method: "POST" });
  if (!res.ok) throw new Error("imagery failed");
  return res.json();
}

export async function fetchParcels(projectId: string): Promise<Parcel[]> {
  return getJson(`/parcels?project_id=${projectId}`);
}

export async function fetchParcel(id: string): Promise<Parcel> {
  return getJson(`/parcels/${id}`);
}

export async function fetchExplanation(id: string): Promise<Explanation> {
  return getJson(`/parcels/${id}/explanation`);
}

export async function verifyParcel(id: string, geom?: Parcel["geom"], correctionType = "boundary_adjust", reviewLabel?: FalsePositiveLabel) {
  const res = await request(`/parcels/${id}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ geom, correction_type: correctionType, review_label: reviewLabel }),
  });
  if (!res.ok) throw new Error("verify failed");
  return res.json();
}

export async function patchParcelGeom(id: string, geom: Parcel["geom"]) {
  const res = await request(`/parcels/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ geom }),
  });
  if (!res.ok) throw new Error("patch failed");
  return res.json();
}

export async function fetchQueue(projectId: string): Promise<SurveyQueueItem[]> {
  return getJson(`/survey-queue?project_id=${projectId}`);
}

export async function fetchChanges(projectId: string): Promise<ChangeDetectionItem[]> {
  return getJson(`/change-detection?project_id=${projectId}`);
}

/** Live review data composed from the existing parcel, evidence, anomaly, and queue APIs. */
export async function fetchReviewWorkspace(projectId: string): Promise<ReviewWorkspace> {
  const [parcels, queue, changes] = await Promise.all([
    fetchParcels(projectId),
    fetchQueue(projectId),
    fetchChanges(projectId),
  ]);
  const evidence = await Promise.all(parcels.map(async (parcel) => {
    try {
      return [parcel.id, await fetchExplanation(parcel.id)] as const;
    } catch {
      return [parcel.id, null] as const;
    }
  }));
  return { parcels, queue, changes, explanations: Object.fromEntries(evidence) };
}

export async function assignSurveyQueueItem(itemId: string, assignedTo: string): Promise<SurveyQueueItem> {
  const res = await request(`/survey-queue/${itemId}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assigned_to: assignedTo }),
  });
  if (!res.ok) throw new Error("survey queue assignment failed");
  return res.json();
}

export type ParcelHistory = { parcel_id: string; versions: { id: string; geom: Parcel["geom"]; captured_at: string; source: string }[] };
export type ParcelComparison = { parcel_id: string; current_area_sqm: number; historical_area_sqm: number | null; area_difference_sqm: number | null; area_difference_percent: number | null; boundary_difference_sqm: number | null; method: string };
export const fetchParcelHistory = (id: string) => getJson<ParcelHistory>(`/parcels/${id}/history`);
export const fetchParcelComparison = (id: string) => getJson<ParcelComparison>(`/parcels/${id}/comparison`);

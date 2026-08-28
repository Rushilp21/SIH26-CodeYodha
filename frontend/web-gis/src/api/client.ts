import type { Explanation, Parcel, Project, SurveyQueueItem } from "@shared/types";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  return getJson("/projects");
}

export async function fetchProjectStatus(id: string) {
  return getJson<{ id: string; name: string; status: string; parcel_count: number }>(
    `/projects/${id}/status`
  );
}

export async function processProject(id: string) {
  const res = await fetch(`${BASE}/projects/${id}/process`, { method: "POST" });
  if (!res.ok) throw new Error("process failed");
  return res.json();
}

export async function uploadImagery(id: string) {
  const res = await fetch(`${BASE}/projects/${id}/imagery`, { method: "POST" });
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

export async function verifyParcel(id: string, geom: Parcel["geom"] | undefined) {
  const res = await fetch(`${BASE}/parcels/${id}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ geom, correction_type: "boundary_adjust" }),
  });
  if (!res.ok) throw new Error("verify failed");
  return res.json();
}

export async function patchParcelGeom(id: string, geom: Parcel["geom"]) {
  const res = await fetch(`${BASE}/parcels/${id}`, {
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

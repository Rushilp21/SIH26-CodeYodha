const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealth() {
  const r = await fetch(`${BASE}/health`);
  if (!r.ok) throw new Error("health failed");
  return r.json() as Promise<{ status: string; service: string }>;
}

export async function fetchProjects() {
  const r = await fetch(`${BASE}/projects`);
  if (!r.ok) throw new Error("projects failed");
  return r.json();
}

export async function fetchVendors() {
  const r = await fetch(`${BASE}/vendors`);
  if (!r.ok) throw new Error("vendors failed");
  return r.json();
}

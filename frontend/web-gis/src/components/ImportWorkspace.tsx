import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, importParcelFile } from "../api/client";

export function ImportWorkspace() {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createdId, setCreatedId] = useState<string | null>(null);
  const navigate = useNavigate();
  async function submit() {
    if (!file || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const content = JSON.parse(await file.text());
      if (content.type !== "FeatureCollection" || !content.features?.length) throw new Error("Select a nonempty GeoJSON FeatureCollection.");
      const id = createdId ?? (await createProject(name.trim())).id;
      setCreatedId(id);
      await importParcelFile(id, content);
      navigate(`/projects/${id}`);
    } catch(e) { setError(e instanceof Error ? e.message : "Import failed"); }
    finally { setBusy(false); }
  }
  return <section className="surface-card" style={{ padding: 20, margin: "20px 0" }}><h2>Open existing GIS / pipeline output</h2><p>Import parcel-only EPSG:4326 GeoJSON into a new project. Your workspace contains data/raw/segmentation/parcels_simplified.geojson. No demo records or model results are generated.</p><div className="review-controls"><label>Project name<input value={name} disabled={!!createdId || busy} onChange={e => setName(e.target.value)} placeholder="Project name" /></label><label>Parcel GeoJSON<input type="file" accept=".geojson,.json" disabled={busy} onChange={e => setFile(e.target.files?.[0] ?? null)} /></label><button className="action-primary" disabled={busy || !file || !name.trim()} onClick={submit}>{busy ? "Importing…" : createdId ? "Retry import" : "Create & import"}</button></div>{error && <p role="alert">{error}{createdId ? " The empty project is preserved for retry." : ""}</p>}</section>;
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, importParcelFile, importPipelineParcelFile } from "../api/client";

export function ImportWorkspace() {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createdId, setCreatedId] = useState<string | null>(null);
  const navigate = useNavigate();
  async function submit() {
    if (!file || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const content = JSON.parse(await file.text());
      const pipelinePayload = Array.isArray(content);
      if (!pipelinePayload && (content.type !== "FeatureCollection" || !content.features?.length)) throw new Error("Select a nonempty parcel GeoJSON FeatureCollection or refined_parcel_payloads.json.");
      let evidence: unknown[] | null = null;
      if (evidenceFile) {
        const parsed = JSON.parse(await evidenceFile.text());
        if (!Array.isArray(parsed) || !parsed.length) throw new Error("The evidence companion must be a nonempty refined_parcel_payloads.json array.");
        if (pipelinePayload) throw new Error("Select either a payload as the primary file or GeoJSON with a payload companion, not both.");
        evidence = parsed;
        const geometryIds = new Set<string>(content.features.map((feature: { properties?: { parcel_id?: unknown } }) => feature.properties?.parcel_id).filter((value: unknown): value is string => typeof value === "string"));
        const evidenceIds = new Set<string>(parsed.map((item: { parcel_id?: unknown }) => item.parcel_id).filter((value: unknown): value is string => typeof value === "string"));
        if (geometryIds.size !== content.features.length || evidenceIds.size !== parsed.length || geometryIds.size !== evidenceIds.size || [...geometryIds].some((id) => !evidenceIds.has(id))) {
          throw new Error("GeoJSON and refined payload parcel IDs do not match. Select files produced by the same pipeline run.");
        }
      }
      const id = createdId ?? (await createProject(name.trim())).id;
      setCreatedId(id);
      if (pipelinePayload) await importPipelineParcelFile(id, content);
      else if (evidence) await importPipelineParcelFile(id, evidence, content);
      else await importParcelFile(id, content);
      navigate(`/projects/${id}`);
    } catch(e) { setError(e instanceof Error ? e.message : "Import failed"); }
    finally { setBusy(false); }
  }
  return <section className="surface-card" style={{ padding: 20, margin: "20px 0" }}><h2>Open existing GIS / pipeline output</h2><p>For complete evidence, select the refined parcel GeoJSON and its matching refined_parcel_payloads.json companion. The backend verifies parcel IDs and geometries before storing confidence, topology, PPO evidence, baseline history, anomalies, health, and review priority.</p><div className="review-controls"><label>Project name<input value={name} disabled={!!createdId || busy} onChange={e => setName(e.target.value)} placeholder="Project name" /></label><label>Parcel GeoJSON or payload<input type="file" accept=".geojson,.json" disabled={busy} onChange={e => setFile(e.target.files?.[0] ?? null)} /></label><label>Evidence companion (recommended)<input type="file" accept=".json" disabled={busy} onChange={e => setEvidenceFile(e.target.files?.[0] ?? null)} /></label><button className="action-primary" disabled={busy || !file || !name.trim()} onClick={submit}>{busy ? "Importing…" : createdId ? "Retry import" : "Create & import"}</button></div><p className="panel-note">A geometry-only import remains supported but cannot display RL, topology, or cadastral health evidence.</p>{error && <p role="alert">{error}{createdId ? " The empty project is preserved for retry." : ""}</p>}</section>;
}

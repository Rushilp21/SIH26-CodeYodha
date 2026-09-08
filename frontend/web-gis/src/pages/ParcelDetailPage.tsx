import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { GeoJSONPolygon } from "@shared/types";
import { fetchExplanation, fetchParcel, patchParcelGeom, verifyParcel } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { ParcelMap } from "../map/ParcelMap";

export function ParcelDetailPage() {
  const { projectId = "", parcelId = "" } = useParams();
  const [revision, setRevision] = useState(0);
  const parcel = useAsync(() => fetchParcel(parcelId), [parcelId, revision]);
  const evidence = useAsync(() => fetchExplanation(parcelId), [parcelId, revision]);
  const [draft, setDraft] = useState("");
  const [preview, setPreview] = useState<GeoJSONPolygon | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { setDraft(parcel.data ? JSON.stringify(parcel.data.geom, null, 2) : ""); setPreview(null); }, [parcel.data]);
  function parse(): GeoJSONPolygon {
    const geom = JSON.parse(draft);
    if (geom.type !== "Polygon" || !Array.isArray(geom.coordinates) || !geom.coordinates.length || geom.coordinates.some((ring: number[][]) => !Array.isArray(ring) || ring.length < 4 || ring.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite) || Math.abs(p[0]) > 180 || Math.abs(p[1]) > 90) || JSON.stringify(ring[0]) !== JSON.stringify(ring[ring.length - 1]))) throw new Error("Enter a Polygon with closed rings and longitude/latitude coordinates. The API also checks topology.");
    return geom;
  }
  async function save(action: "edit" | "verify" | "reject") {
    if (!window.confirm(action === "edit" ? "Save this boundary? Existing confidence evidence will be invalidated pending re-analysis." : `Mark this parcel ${action === "verify" ? "verified" : "rejected"} and complete its active survey entries?`)) return;
    setBusy(true); setMessage("");
    try {
      if (action === "edit") await patchParcelGeom(parcelId, parse());
      else await verifyParcel(parcelId, undefined, action === "reject" ? "reject" : "boundary_adjust");
      setMessage("Saved to the backend."); setRevision(x => x + 1);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Save failed"); }
    finally { setBusy(false); }
  }
  return <div className="page-content"><Link to={`/projects/${projectId}/queue`}>← Review queue</Link><h1>Parcel boundary review</h1><p>{parcelId}</p>
    {parcel.loading && <p role="status">Loading parcel…</p>}{parcel.error && <p role="alert">{parcel.error}</p>}
    {parcel.data && <><p>Status: {parcel.data.status} · Confidence: {parcel.data.confidence_score ?? "Unavailable"} · Health: {parcel.data.health_score ?? "Unavailable"}</p><ParcelMap parcels={[{ ...parcel.data, geom: preview ?? parcel.data.geom }]} selectedId={parcelId} />
    <section className="surface-card" style={{ padding: 20, marginTop: 20 }}><h2>Boundary editor</h2><p>EPSG:4326 GeoJSON. Preview edits before saving. Verification uses the saved boundary, not an unsaved preview.</p><textarea aria-label="Polygon GeoJSON" rows={12} style={{ width: "100%", fontFamily: "monospace", border: "1px solid #cbd5e1", padding: 12 }} value={draft} onChange={e => setDraft(e.target.value)} />
    <div className="parcel-actions"><button className="action-secondary" onClick={() => { try { setPreview(parse()); setMessage("Unsaved preview"); } catch(e) { setMessage(String(e)); } }}>Preview boundary</button><button className="action-primary" disabled={busy || parcel.loading} onClick={() => save("edit")}>Save boundary</button><button className="action-secondary" disabled={busy || parcel.data.status === "verified"} onClick={() => save("verify")}>Verify saved boundary</button><button className="action-secondary" disabled={busy || parcel.data.status === "rejected"} onClick={() => save("reject")}>Reject parcel</button></div></section>
    <section className="surface-card" style={{ padding: 20, marginTop: 20 }}><h2>Explainable evidence</h2>{evidence.error && <p role="alert">{evidence.error}</p>}<p>{evidence.data?.explanation}</p>{evidence.data?.components.map((c,i) => <p key={i}><strong>{c.component}: {c.score.toFixed(3)}</strong> — {c.explanation}</p>)}</section></>}
    {message && <p role="status">{message}</p>}
  </div>;
}

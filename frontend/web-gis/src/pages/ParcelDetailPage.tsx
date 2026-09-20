import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { GeoJSONPolygon } from "@shared/types";
import { fetchExplanation, fetchParcel, patchParcelGeom, verifyParcel, type FalsePositiveLabel } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { EditableParcelMap } from "../map/EditableParcelMap";
import { editableVertexCount, simplifyGeometryForEditing } from "../map/geometryEditing";

function percent(value: number | null | undefined) { return value == null ? "—" : `${Math.round(value * 100)}%`; }
function componentLabel(value: string) {
  return ({ segmentation: "Segmentation", topology: "Topology", edge_alignment: "Edge alignment", deviation_from_baseline: "Baseline agreement", rl_refinement: "Post-PPO alignment" } as Record<string, string>)[value] ?? value.replace(/_/g, " ");
}

export function ParcelDetailPage() {
  const { projectId = "", parcelId = "" } = useParams();
  const navigate = useNavigate();
  const [revision, setRevision] = useState(0);
  const parcel = useAsync(() => fetchParcel(parcelId), [parcelId, revision]);
  const evidence = useAsync(() => fetchExplanation(parcelId), [parcelId, revision]);
  const [editedGeometry, setEditedGeometry] = useState<GeoJSONPolygon | null>(null);
  const [boundaryTouched, setBoundaryTouched] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [rejectLabel, setRejectLabel] = useState<FalsePositiveLabel>("false_positive_building");

  useEffect(() => {
    setEditedGeometry(parcel.data ? simplifyGeometryForEditing(parcel.data.geom) : null);
    setBoundaryTouched(false);
  }, [parcel.data]);
  const dirty = useMemo(() => Boolean(boundaryTouched && parcel.data && editedGeometry), [boundaryTouched, parcel.data, editedGeometry]);
  const manuallyEdited = Boolean(parcel.data && parcel.data.version > 1 && parcel.data.confidence_score == null && parcel.data.health_score == null);

  async function save(action: "edit" | "verify" | "reject") {
    const rejectReason = action === "reject" ? ` as ${rejectLabel.replace(/_/g, " ")}` : "";
    const prompt = `Mark this parcel ${action === "verify" ? "verified" : `rejected${rejectReason}`} and complete its active survey entries?`;
    if (action !== "edit" && !window.confirm(prompt)) return;
    setBusy(true);
    setMessage("");
    try {
      if (action === "edit") {
        if (!editedGeometry) throw new Error("Boundary is unavailable.");
        await patchParcelGeom(parcelId, editedGeometry);
        navigate(`/projects/${projectId}?parcel=${encodeURIComponent(parcelId)}`, { replace: true });
        return;
      } else {
        await verifyParcel(parcelId, undefined, action === "reject" ? "reject" : "boundary_adjust", action === "reject" ? rejectLabel : undefined);
      }
      setMessage("Saved.");
      setRevision((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return <div className="page-content parcel-review-page">
    <Link to={`/projects/${projectId}/queue`} className="back-link">← Review queue</Link>
    <div className="parcel-review-heading"><div><h1>Parcel boundary review</h1><span>{parcelId}</span></div>{parcel.data && (manuallyEdited ? <span className="manual-edit-badge">Boundary edited</span> : <div className="parcel-review-scores"><span>Confidence <strong>{percent(parcel.data.confidence_score)}</strong></span><span>Health <strong>{percent(parcel.data.health_score)}</strong></span></div>)}</div>
    {parcel.loading && <p role="status">Loading parcel…</p>}
    {parcel.error && <p role="alert">{parcel.error}</p>}

    {parcel.data && editedGeometry && <>
      <section className="boundary-editor-card">
        <div className="boundary-editor-title"><div><h2>Edit boundary</h2><p>Drag a corner point, then save.</p></div><div className="boundary-editor-meta"><span>{editableVertexCount(editedGeometry)} points</span>{dirty && <b>Unsaved</b>}</div></div>
        <EditableParcelMap geometry={editedGeometry} onChange={(geometry) => { setEditedGeometry(geometry); setBoundaryTouched(true); }} />
        <div className="boundary-editor-actions">
          <button type="button" className="action-secondary" disabled={!dirty || busy} onClick={() => { setEditedGeometry(simplifyGeometryForEditing(parcel.data!.geom)); setBoundaryTouched(false); }}>Reset</button>
          <button type="button" className="action-primary" disabled={!dirty || busy} onClick={() => save("edit")}>{busy ? "Saving…" : "Save boundary"}</button>
          <button type="button" className="action-secondary" title={dirty ? "Save boundary changes before verification" : undefined} disabled={busy || dirty || parcel.data.status === "verified"} onClick={() => save("verify")}>Verify boundary</button>
        </div>
        <div className="false-positive-actions compact-rejection"><label>False-positive reason<select value={rejectLabel} onChange={(event) => setRejectLabel(event.target.value as FalsePositiveLabel)}><option value="false_positive_building">Building</option><option value="false_positive_road">Road</option><option value="false_positive_canal">Canal</option><option value="false_positive_other">Other</option></select></label><button type="button" disabled={busy || parcel.data.status === "rejected"} onClick={() => save("reject")}>Reject & label</button></div>
        {message && <p className="action-feedback" role="status">{message}</p>}
      </section>

      <section className="surface-card compact-evidence">
        <div className="section-header"><h2>Evidence</h2>{evidence.loading && <span>Loading…</span>}</div>
        {evidence.error && <p role="alert">Evidence unavailable: {evidence.error}</p>}
        <div className="compact-evidence-grid">{evidence.data?.components.map((component, index) => <div key={`${component.component}-${index}`}><span>{componentLabel(component.component)}</span><strong>{percent(component.score)}</strong></div>)}</div>
      </section>
    </>}
  </div>;
}

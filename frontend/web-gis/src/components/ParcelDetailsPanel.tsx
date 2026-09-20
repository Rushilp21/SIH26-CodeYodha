import type { CSSProperties, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { Explanation, Parcel } from "@shared/types";
import type { ChangeDetectionItem, FalsePositiveLabel } from "../api/client";
import { Icon } from "./Icon";
import { fetchParcelHistory } from "../api/client";
import { useAsync } from "../hooks/useAsync";

type Props = {
  projectId: string;
  parcel: Parcel | null;
  explanation: Explanation | null;
  explanationLoading: boolean;
  explanationError: string | null;
  anomaliesLoading: boolean;
  anomaliesError: string | null;
  anomalies: ChangeDetectionItem[];
  verifying: boolean;
  feedback: string | null;
  onClose: () => void;
  onVerify: () => void;
  onReject: (label: FalsePositiveLabel) => void;
};

function percentage(value: number | null) { return value == null ? null : Math.round(value * 100); }
function date(value: string | null | undefined) { return value && Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)) : "Not supplied by API"; }

export function ParcelDetailsPanel({ projectId, parcel, explanation, explanationLoading, explanationError, anomaliesLoading, anomaliesError, anomalies, verifying, feedback, onClose, onVerify, onReject }: Props) {
  const history = useAsync(async () => parcel ? fetchParcelHistory(parcel.id) : null, [parcel?.id, parcel?.version]);
  if (!parcel) return <aside className="parcel-panel empty"><Icon name="map" size={34} /><strong>Select a parcel</strong><span>Click a colored boundary to inspect its live cadastral record.</span></aside>;

  const confidence = percentage(parcel.confidence_score);
  const health = percentage(parcel.health_score);
  const manuallyEdited = parcel.version > 1 && parcel.confidence_score == null && parcel.health_score == null;
  const topology = explanation?.components.find((component) => component.component === "topology");
  const segmentation = explanation?.components.find((component) => component.component === "segmentation");
  const edgeAlignment = explanation?.components.find((component) => component.component === "edge_alignment");
  const baselineAgreement = explanation?.components.find((component) => component.component === "deviation_from_baseline");
  const refinement = explanation?.components.find((component) => component.component === "rl_refinement");
  const isAi = parcel.source === "ai_extracted";

  return <aside className="parcel-panel">
    <div className="parcel-panel-header"><div><strong>{parcel.id.slice(0, 12)}</strong><span>{parcel.land_use ?? "Land use not supplied"} · v{parcel.version}</span></div><button type="button" className="panel-close" onClick={onClose} aria-label="Close parcel details">×</button></div>
    <div className="parcel-panel-body">
      <section className="confidence-block">
        <div className="confidence-ring" style={{ "--score": `${confidence ?? 0}%` } as CSSProperties}><span>{manuallyEdited ? "Edited" : confidence == null ? "n/a" : `${confidence}%`}</span></div>
        <div><p>{manuallyEdited ? "Boundary edited" : "Boundary confidence"}</p><strong className={`status-label ${parcel.status}`}>{manuallyEdited ? "Scores removed" : parcel.status.replace("_", " ")}</strong>{!manuallyEdited && <span>{health == null ? "Health unavailable" : `Health ${health}%`}</span>}</div>
      </section>

      <PanelSection title="AI processing stage"><div className="pipeline-stages"><span className="done">Imported</span><span className={isAi ? "done" : ""}>AI extracted</span><span className={refinement ? "done current" : ""}>{refinement ? "PPO refined" : "RL unavailable"}</span><span className={topology ? "done" : ""}>{topology ? "Topology checked" : "Validation unavailable"}</span><span className={parcel.status === "verified" ? "done current" : ""}>Verified</span></div></PanelSection>

      <PanelSection title="Parcel information"><Info label="Source" value={parcel.source.split("_").join(" ")} /><Info label="Land use" value={parcel.land_use ?? "Not supplied"} /><Info label="Area" value={parcel.area_sqm == null ? "Not supplied" : `${parcel.area_sqm.toLocaleString()} m²`} /><Info label="Health score" value={health == null ? "Not supplied" : `${health}%`} /></PanelSection>

      <PanelSection title="Topology & refinement">{explanationError && <p role="alert" className="panel-note">Evidence unavailable</p>}{explanationLoading ? <p className="panel-note">Loading…</p> : null}<Info label="Segmentation" value={segmentation ? `${percentage(segmentation.score)}%` : "—"} /><Info label="Topology" value={topology ? `${percentage(topology.score)}%` : "—"} /><Info label="Edge alignment" value={edgeAlignment ? `${percentage(edgeAlignment.score)}%` : "—"} /><Info label="Baseline agreement" value={baselineAgreement ? `${percentage(baselineAgreement.score)}%` : "—"} /><Info label="Post-PPO alignment" value={refinement ? `${percentage(refinement.score)}%` : "—"} /></PanelSection>

      <PanelSection title={`Potential anomalies${anomalies.length ? ` (${anomalies.length})` : ""}`}>{anomaliesLoading ? <p className="panel-note">Loading…</p> : anomaliesError ? <p role="alert" className="panel-note">Unavailable</p> : anomalies.length ? anomalies.map((anomaly, index) => <article className="anomaly-card" key={`${anomaly.type}-${anomaly.detected_at ?? "undated"}-${index}`}><strong>{anomaly.type}</strong><span>Magnitude {anomaly.magnitude.toFixed(2)}</span></article>) : <p className="panel-note">None</p>}</PanelSection>

      <PanelSection title="Boundary history">{history.loading && <p>Loading…</p>}{history.error && <p role="alert">Unavailable</p>}<div className="record-timeline">{history.data?.versions.map(v => <div key={v.id}><i /><strong>{v.source}</strong><span>{date(v.captured_at)}</span></div>)}<div><i /><strong>Current version {parcel.version}</strong><span>{date(parcel.updated_at)}</span></div></div></PanelSection>

      <PanelSection title="Actions"><div className="parcel-actions"><button type="button" className="action-primary" disabled={verifying || parcel.status === "verified" || parcel.status === "rejected"} onClick={onVerify}><Icon name="check" size={14} />{verifying ? "Saving…" : parcel.status === "verified" ? "Verified" : "Verify boundary"}</button><Link className="action-secondary" to={`/projects/${projectId}/parcels/${parcel.id}`}>Edit geometry</Link><Link className="action-secondary" to={`/projects/${projectId}/queue`}>Open review queue</Link></div><div className="false-positive-actions"><p>Reject obvious false parcel as</p><button type="button" disabled={verifying || parcel.status === "rejected"} onClick={() => onReject("false_positive_building")}>Building</button><button type="button" disabled={verifying || parcel.status === "rejected"} onClick={() => onReject("false_positive_road")}>Road</button><button type="button" disabled={verifying || parcel.status === "rejected"} onClick={() => onReject("false_positive_canal")}>Canal</button><button type="button" disabled={verifying || parcel.status === "rejected"} onClick={() => onReject("false_positive_other")}>Other</button></div>{feedback ? <p className="action-feedback">{feedback}</p> : null}</PanelSection>
    </div>
  </aside>;
}

function PanelSection({ title, children }: { title: string; children: ReactNode }) { return <section className="parcel-section"><h2>{title}</h2>{children}</section>; }
function Info({ label, value }: { label: string; value: string }) { return <div className="parcel-info"><span>{label}</span><strong>{value}</strong></div>; }

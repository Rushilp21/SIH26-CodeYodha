import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingState, StatusBadge } from "@shared/components";
import type { Explanation, Parcel, SurveyQueueItem } from "@shared/types";
import { assignSurveyQueueItem, fetchReviewWorkspace, verifyParcel, type ChangeDetectionItem } from "../api/client";
import { topologyErrors } from "../data/changeDetection";
import { Icon } from "../components/Icon";
import { useAsync } from "../hooks/useAsync";

type Tab = "all" | "review" | "field" | "verified";

export function ReviewQueuePage() {
  const { projectId = "" } = useParams();
  const [revision, setRevision] = useState(0);
  const workspace = useAsync(() => fetchReviewWorkspace(projectId), [projectId, revision]);
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("confidence");
  const [selectedId, setSelectedId] = useState<string | null>(params.get("parcel"));
  const [assignee, setAssignee] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);

  const rows = useMemo(() => (workspace.data?.parcels ?? []).map((parcel) => ({
    parcel,
    explanation: workspace.data?.explanations[parcel.id] ?? null,
    anomalies: (workspace.data?.changes ?? []).filter((change) => change.parcel_id === parcel.id),
    queueItem: (workspace.data?.queue ?? []).find((item) => item.parcel_id === parcel.id) ?? null,
  })), [workspace.data]);
  const visibleRows = rows.filter((row) => tab === "all" ? true : tab === "review" ? row.parcel.status === "needs_review" || row.parcel.status === "rejected" : tab === "field" ? Boolean(row.queueItem) : row.parcel.status === "verified").filter((row) => `${row.parcel.id} ${row.parcel.land_use ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  const selected = rows.find((row) => row.parcel.id === selectedId) ?? null;
  const counts = { all: rows.length, review: rows.filter((row) => row.parcel.status === "needs_review" || row.parcel.status === "rejected").length, field: rows.filter((row) => row.queueItem).length, verified: rows.filter((row) => row.parcel.status === "verified").length };

  async function assignSelected() {
    if (!selected?.queueItem || !assignee.trim()) return;
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(assignee.trim())) {
      setActionMessage("Enter a valid surveyor UUID.");
      return;
    }
    setAssigning(true);
    setActionMessage(null);
    try {
      const updated = await assignSurveyQueueItem(selected.queueItem.id, assignee.trim());
      workspace.setData((current) => current ? { ...current, queue: current.queue.map((item) => item.id === updated.id ? updated : item) } : current);
      setActionMessage("Survey queue assignment saved.");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Assignment could not be saved.");
    } finally { setAssigning(false); }
  }

  return (
    <div className="review-workspace">
      <section className="review-main">
        <div className="review-header"><div><Link className="back-link" to={`/projects/${projectId}`}>← Map workspace</Link><h1>Review prioritization queue</h1><p>Confidence, health, topology evidence, RL refinement, anomalies, and survey priority come from the target APIs.</p></div></div>
        {workspace.loading ? <LoadingState label="Loading review evidence…" /> : null}
        {workspace.error ? <ErrorState message={workspace.error} /> : null}
        {workspace.data && !workspace.loading && !workspace.error ? <>
          <div className="review-tabs">{(["all", "review", "field", "verified"] as Tab[]).map((key) => <button key={key} type="button" onClick={() => setTab(key)} className={tab === key ? "active" : ""}>{key === "all" ? "All parcels" : key === "review" ? "Review required" : key === "field" ? "Survey queue" : "Verified"}<span>{counts[key]}</span></button>)}</div>
          <div className="review-controls"><label>Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Parcel ID or land use" /></label><label>Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="confidence">Lowest confidence</option><option value="priority">Highest survey priority</option></select></label></div>
          <p className="panel-note">Anomaly values are individual event magnitudes. An overall anomaly score and RL job status are not exposed by the current service.</p>
          <div className="review-table-wrap"><table className="review-table"><thead><tr><th>Parcel</th><th>Confidence</th><th>Health</th><th>Anomaly magnitudes</th><th>Topology</th><th>RL refinement</th><th>Field verification</th><th>Priority</th></tr></thead><tbody>{visibleRows.length ? visibleRows.sort((a, b) => sort === "priority" ? (b.queueItem?.priority_score ?? -Infinity) - (a.queueItem?.priority_score ?? -Infinity) : (a.parcel.confidence_score ?? Infinity) - (b.parcel.confidence_score ?? Infinity)).map((row) => <ReviewRow key={row.parcel.id} row={row} selected={selectedId === row.parcel.id} onSelect={() => { setSelectedId(row.parcel.id); setAssignee(""); setActionMessage(null); }} />) : <tr><td colSpan={8}><div className="review-empty">No live records match this queue.</div></td></tr>}</tbody></table></div>
        </> : null}
      </section>
      <ReviewDetail projectId={projectId} selected={selected} assignee={assignee} onAssignee={setAssignee} assigning={assigning} message={actionMessage} onAssign={assignSelected} onClose={() => { setSelectedId(null); setActionMessage(null); }} />
      {selected && <div className="review-decision"><ReviewDecision parcel={selected.parcel} onChanged={() => setRevision(x => x + 1)} /></div>}
    </div>
  );
}

type ReviewRowData = { parcel: Parcel; explanation: Explanation | null; anomalies: ChangeDetectionItem[]; queueItem: SurveyQueueItem | null };

function ReviewRow({ row, selected, onSelect }: { row: ReviewRowData; selected: boolean; onSelect: () => void }) {
  const topology = row.explanation?.components.find((component) => component.component === "topology");
  const hasTopologyError = topologyErrors(row.anomalies).length > 0;
  const anomalyValues = row.anomalies.map((anomaly) => anomaly.magnitude.toFixed(3)).join(", ");
  const refinement = "Status unavailable";
  return <tr className={selected ? "selected" : ""} tabIndex={0} aria-selected={selected} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); } }} onClick={onSelect}><td><strong>{row.parcel.id.slice(0, 12)}</strong><span>{row.parcel.land_use ?? "Land use unavailable"}</span></td><td><Score score={row.parcel.confidence_score} /></td><td><Score score={row.parcel.health_score} compact /></td><td>{row.anomalies.length ? <span className="anomaly-score">{anomalyValues} <small>{row.anomalies.length} event{row.anomalies.length === 1 ? "" : "s"}</small></span> : <span className="muted-cell">None</span>}</td><td>{topology || hasTopologyError ? <span className={hasTopologyError ? "topology-error" : "muted-cell"}>{hasTopologyError ? "Error" : `${Math.round((topology?.score ?? 0) * 100)}% score`}</span> : <span className="muted-cell">No evidence</span>}</td><td><span className="refinement-status">{refinement}</span></td><td><StatusBadge status={row.parcel.source === "field_verified" ? "verified" : row.queueItem ? row.queueItem.status : row.parcel.status} /></td><td>{row.queueItem ? <span className="priority-score">{row.queueItem.priority_score.toFixed(2)}</span> : <span className="muted-cell">—</span>}</td></tr>;
}

function Score({ score, compact = false }: { score: number | null; compact?: boolean }) { const value = score == null ? null : Math.round(score * 100); return <span className={`score-pill ${compact ? "compact" : ""}`}>{value == null ? "n/a" : `${value}%`}</span>; }

function ReviewDetail({ projectId, selected, assignee, onAssignee, assigning, message, onAssign, onClose }: { projectId: string; selected: ReviewRowData | null; assignee: string; onAssignee: (value: string) => void; assigning: boolean; message: string | null; onAssign: () => void; onClose: () => void }) {
  if (!selected) return <aside className="review-panel empty"><Icon name="queue" size={34} /><strong>Select a queue record</strong><span>Its full live evidence is shown here.</span></aside>;
  const topology = selected.explanation?.components.find((component) => component.component === "topology");
  return <aside className="review-panel"><div className="parcel-panel-header"><div><strong>{selected.parcel.id.slice(0, 12)}</strong><span>{selected.parcel.status.replace("_", " ")} · {selected.parcel.source.replace("_", " ")}</span></div><button type="button" className="panel-close" onClick={onClose} aria-label="Close review details">×</button></div><div className="review-panel-body"><section><h2>Review evidence</h2><Info label="Confidence" value={formatPercent(selected.parcel.confidence_score)} /><Info label="Cadastral health" value={formatPercent(selected.parcel.health_score)} /><Info label="Topology" value={topology ? `${formatPercent(topology.score)} · ${topology.explanation}` : "No topology evidence returned"} /><Info label="RL evidence" value="Job status not exposed; component evidence is available in parcel details." /></section><section><h2>Detected anomalies</h2>{selected.anomalies.length ? selected.anomalies.map((anomaly, index) => <div className="anomaly-card" key={`${anomaly.type}-${index}`}><strong>{anomaly.type}</strong><span>Magnitude {anomaly.magnitude.toFixed(2)}</span></div>) : <p className="panel-note">No anomalies returned for this parcel.</p>}</section><section><h2>Actions</h2><div className="review-actions"><Link className="action-primary" to={`/projects/${projectId}/parcels/${selected.parcel.id}`}>Open parcel & verify</Link><Link className="action-secondary" to={`/projects/${projectId}?parcel=${encodeURIComponent(selected.parcel.id)}`}>Locate on map</Link></div>{selected.queueItem ? <div className="assignment-box"><label htmlFor="assignee">Assign survey queue item</label><input id="assignee" value={assignee} onChange={(event) => onAssignee(event.target.value)} placeholder="Assignee UUID" /><button type="button" disabled={!assignee.trim() || assigning} onClick={onAssign}>{assigning ? "Assigning…" : "Save assignment"}</button><p>Uses the existing survey-queue assignment API.</p></div> : <p className="panel-note">This parcel has no survey-queue item to assign.</p>}{message ? <p className="action-feedback">{message}</p> : null}</section></div></aside>;
}

function Info({ label, value }: { label: string; value: string }) { return <div className="review-info"><span>{label}</span><strong>{value}</strong></div>; }
function formatPercent(score: number | null) { return score == null ? "Not supplied" : `${Math.round(score * 100)}%`; }

function ReviewDecision({ parcel, onChanged }: { parcel: Parcel; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function decide(reject: boolean) {
    if (!window.confirm(`${reject ? "Reject" : "Verify"} parcel ${parcel.id}? Its active survey queue entries will be completed.`)) return;
    setBusy(true); setError("");
    try { await verifyParcel(parcel.id, undefined, reject ? "reject" : "boundary_adjust"); onChanged(); }
    catch(e) { setError(e instanceof Error ? e.message : "Unable to save decision"); }
    finally { setBusy(false); }
  }
  return <><button className="action-primary" disabled={busy || parcel.status === "verified"} onClick={() => decide(false)}>Verify selected</button><button className="action-secondary" disabled={busy || parcel.status === "rejected"} onClick={() => decide(true)}>Reject selected</button>{error && <p role="alert">{error}</p>}</>;
}

import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingState, StatusBadge } from "@shared/components";
import type { Explanation, Parcel, SurveyQueueItem } from "@shared/types";
import { assignSurveyQueueItem, fetchReviewLabelExport, fetchReviewWorkspace, verifyParcel, type ChangeDetectionItem, type FalsePositiveLabel } from "../api/client";
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
  const [exporting, setExporting] = useState(false);

  const rows = useMemo(() => (workspace.data?.parcels ?? []).map((parcel) => ({
    parcel,
    explanation: workspace.data?.explanations[parcel.id] ?? null,
    anomalies: (workspace.data?.changes ?? []).filter((change) => change.parcel_id === parcel.id),
    queueItem: (workspace.data?.queue ?? []).find((item) => item.parcel_id === parcel.id) ?? null,
  })), [workspace.data]);
  const visibleRows = rows.filter((row) => tab === "all" ? true : tab === "review" ? row.parcel.status === "needs_review" || row.parcel.status === "rejected" : tab === "field" ? Boolean(row.queueItem) : row.parcel.status === "verified").filter((row) => `${row.parcel.id} ${row.parcel.land_use ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  const selected = rows.find((row) => row.parcel.id === selectedId) ?? null;
  const counts = { all: rows.length, review: rows.filter((row) => row.parcel.status === "needs_review" || row.parcel.status === "rejected").length, field: rows.filter((row) => row.queueItem).length, verified: rows.filter((row) => row.parcel.status === "verified").length };
  const labelledNegatives = rows.filter((row) => row.anomalies.some((item) => item.type.startsWith("false_positive_"))).length;
  const reviewedTotal = counts.verified + labelledNegatives;
  const trainingReady = reviewedTotal >= 100 && counts.verified >= 40 && labelledNegatives >= 40;

  async function downloadLabels() {
    setExporting(true);
    setActionMessage(null);
    try {
      const exported = await fetchReviewLabelExport(projectId);
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/geo+json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `bhumisetu-review-labels-${projectId}.geojson`;
      link.click();
      URL.revokeObjectURL(url);
      setActionMessage(`Exported ${exported.summary.eligible_reviewed_labels} explicit review labels.`);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "Review labels could not be exported.");
    } finally { setExporting(false); }
  }

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
        <div className="review-header"><div><Link className="back-link" to={`/projects/${projectId}`}>← Map workspace</Link><h1>Review queue</h1></div><button type="button" className="export-labels-button" disabled={exporting || reviewedTotal === 0} onClick={downloadLabels}>{exporting ? "Preparing export…" : "Export labels"}</button></div>
        {workspace.loading ? <LoadingState label="Loading review evidence…" /> : null}
        {workspace.error ? <ErrorState message={workspace.error} /> : null}
        {workspace.data && !workspace.loading && !workspace.error ? <>
          <div className={`review-coverage ${trainingReady ? "ready" : "collecting"}`}><div><span>Reviewed labels</span><strong>{reviewedTotal} / 100 minimum</strong></div><div><span>Verified boundaries</span><strong>{counts.verified} / 40</strong></div><div><span>False positives</span><strong>{labelledNegatives} / 40</strong></div><b>{trainingReady ? "Dataset coverage ready" : "Continue visual review"}</b></div>
          <div className="review-tabs">{(["all", "review", "field", "verified"] as Tab[]).map((key) => <button key={key} type="button" onClick={() => setTab(key)} className={tab === key ? "active" : ""}>{key === "all" ? "All parcels" : key === "review" ? "Review required" : key === "field" ? "Survey queue" : "Verified"}<span>{counts[key]}</span></button>)}</div>
          <div className="review-controls"><label>Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Parcel ID or land use" /></label><label>Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="confidence">Lowest confidence</option><option value="priority">Highest survey priority</option></select></label></div>
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
  const rl = row.explanation?.components.find((component) => component.component === "rl_refinement");
  const hasTopologyError = topologyErrors(row.anomalies).length > 0;
  const anomalyValues = row.anomalies.map((anomaly) => anomaly.magnitude.toFixed(3)).join(", ");
  const refinement = rl ? `PPO ${Math.round(rl.score * 100)}%` : "No evidence";
  const manuallyEdited = row.parcel.version > 1 && row.parcel.confidence_score == null && row.parcel.health_score == null;
  return <tr className={selected ? "selected" : ""} tabIndex={0} aria-selected={selected} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); } }} onClick={onSelect}><td><strong>{row.parcel.id.slice(0, 12)}</strong>{row.parcel.land_use ? <span>{row.parcel.land_use}</span> : null}</td><td>{manuallyEdited ? <span className="edited-score">Boundary edited</span> : <Score score={row.parcel.confidence_score} />}</td><td>{manuallyEdited ? <span className="muted-cell">—</span> : <Score score={row.parcel.health_score} compact />}</td><td>{row.anomalies.length ? <span className="anomaly-score">{anomalyValues} <small>{row.anomalies.length} event{row.anomalies.length === 1 ? "" : "s"}</small></span> : <span className="muted-cell">None</span>}</td><td>{topology || hasTopologyError ? <span className={hasTopologyError ? "topology-error" : "muted-cell"}>{hasTopologyError ? "Error" : `${Math.round((topology?.score ?? 0) * 100)}% score`}</span> : <span className="muted-cell">No evidence</span>}</td><td><span className="refinement-status">{refinement}</span></td><td><StatusBadge status={row.parcel.source === "field_verified" ? "verified" : row.queueItem ? row.queueItem.status : row.parcel.status} /></td><td>{row.queueItem ? <span className="priority-score">{row.queueItem.priority_score.toFixed(2)}</span> : <span className="muted-cell">—</span>}</td></tr>;
}

function Score({ score, compact = false }: { score: number | null; compact?: boolean }) { const value = score == null ? null : Math.round(score * 100); return <span className={`score-pill ${compact ? "compact" : ""}`}>{value == null ? "n/a" : `${value}%`}</span>; }

function ReviewDetail({ projectId, selected, assignee, onAssignee, assigning, message, onAssign, onClose }: { projectId: string; selected: ReviewRowData | null; assignee: string; onAssignee: (value: string) => void; assigning: boolean; message: string | null; onAssign: () => void; onClose: () => void }) {
  if (!selected) return <aside className="review-panel empty"><Icon name="queue" size={34} /><strong>Select a parcel</strong></aside>;
  const component = (name: string) => selected.explanation?.components.find((item) => item.component === name);
  const topology = component("topology");
  const segmentation = component("segmentation");
  const alignment = component("edge_alignment");
  const baseline = component("deviation_from_baseline");
  const rl = component("rl_refinement");
  const manuallyEdited = selected.parcel.version > 1 && selected.parcel.confidence_score == null && selected.parcel.health_score == null;
  return <aside className="review-panel"><div className="parcel-panel-header"><div><strong>{selected.parcel.id.slice(0, 12)}</strong><span>{selected.parcel.status.replace("_", " ")} · {selected.parcel.source.replace("_", " ")}</span></div><button type="button" className="panel-close" onClick={onClose} aria-label="Close review details">×</button></div><div className="review-panel-body"><section><h2>Review evidence</h2><Info label="Confidence" value={manuallyEdited ? "Boundary edited" : formatPercent(selected.parcel.confidence_score)} /><Info label="Cadastral health" value={manuallyEdited ? "Score removed" : formatPercent(selected.parcel.health_score)} /><Info label="Segmentation" value={formatEvidence(segmentation)} /><Info label="Topology" value={formatEvidence(topology)} /><Info label="Edge alignment" value={formatEvidence(alignment)} /><Info label="Baseline agreement" value={formatEvidence(baseline)} /><Info label="Post-PPO alignment" value={formatEvidence(rl)} /></section><section><h2>Detected anomalies & labels</h2>{selected.anomalies.length ? selected.anomalies.map((anomaly, index) => <div className="anomaly-card" key={`${anomaly.type}-${index}`}><strong>{anomaly.type}</strong><span>Magnitude {anomaly.magnitude.toFixed(2)}</span></div>) : <p className="panel-note">None</p>}</section><section><h2>Actions</h2><div className="review-actions"><Link className="action-primary" to={`/projects/${projectId}/parcels/${selected.parcel.id}`}>Open parcel & verify</Link><Link className="action-secondary" to={`/projects/${projectId}?parcel=${encodeURIComponent(selected.parcel.id)}`}>Locate on map</Link></div>{selected.queueItem ? <div className="assignment-box"><label htmlFor="assignee">Assign surveyor</label><input id="assignee" value={assignee} onChange={(event) => onAssignee(event.target.value)} placeholder="Assignee UUID" /><button type="button" disabled={!assignee.trim() || assigning} onClick={onAssign}>{assigning ? "Assigning…" : "Save assignment"}</button></div> : null}{message ? <p className="action-feedback">{message}</p> : null}</section></div></aside>;
}

function Info({ label, value }: { label: string; value: string }) { return <div className="review-info"><span>{label}</span><strong>{value}</strong></div>; }
function formatPercent(score: number | null) { return score == null ? "Not supplied" : `${Math.round(score * 100)}%`; }
function formatEvidence(component: Explanation["components"][number] | undefined) { return component ? `${Math.round(component.score * 100)}%` : "—"; }

function ReviewDecision({ parcel, onChanged }: { parcel: Parcel; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [label, setLabel] = useState<FalsePositiveLabel>("false_positive_building");
  async function decide(reject: boolean) {
    const reason = reject ? ` as ${label.replace(/_/g, " ")}` : "";
    if (!window.confirm(`${reject ? "Reject" : "Verify"} parcel ${parcel.id}${reason}? Its active survey queue entries will be completed.`)) return;
    setBusy(true); setError("");
    try { await verifyParcel(parcel.id, undefined, reject ? "reject" : "boundary_adjust", reject ? label : undefined); onChanged(); }
    catch(e) { setError(e instanceof Error ? e.message : "Unable to save decision"); }
    finally { setBusy(false); }
  }
  return <><button className="action-primary" disabled={busy || parcel.status === "verified"} onClick={() => decide(false)}>Verify selected</button><label className="review-label-select">False-positive reason<select value={label} onChange={(event) => setLabel(event.target.value as FalsePositiveLabel)}><option value="false_positive_building">Building</option><option value="false_positive_road">Road</option><option value="false_positive_canal">Canal</option><option value="false_positive_other">Other</option></select></label><button className="action-danger" disabled={busy || parcel.status === "rejected"} onClick={() => decide(true)}>Reject & label</button>{error && <p role="alert">{error}</p>}</>;
}

import { useState } from "react";
import { fetchDashboardSnapshot } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { dashboardMetrics } from "../data/dashboardMetrics";
import "../styles/analytics.css";

function distribution(values: string[]) {
  return Object.entries(values.reduce<Record<string, number>>((counts, value) => { counts[value] = (counts[value] ?? 0) + 1; return counts; }, {}));
}
function Bars({ title, values }: { title: string; values: string[] }) {
  const rows = distribution(values);
  return <article className="surface-card analytics-card"><h2>{title}</h2>{!rows.length && <p>No records available.</p>}{rows.map(([label, count]) => <div className="analytics-row" key={label}><span>{label.replace(/_/g, " ")}</span><meter min={0} max={Math.max(values.length, 1)} value={count} /><strong>{count}</strong></div>)}</article>;
}
export function AnalyticsPage() {
  const [revision, setRevision] = useState(0);
  const { data, loading, error } = useAsync(fetchDashboardSnapshot, [revision]);
  const parcels = data?.parcels ?? [];
  const metrics = dashboardMetrics(parcels, data?.queue ?? []);
  const health = parcels.flatMap(p => p.health_score == null ? [] : [p.health_score]);
  function download() {
    if (!data) return;
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), provenance: "Stored API records; project.demo identifies seeded projects", ...data }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = "bhumisetu-records.json"; link.click(); URL.revokeObjectURL(url);
  }
  return <div className="page-content"><div className="dashboard-intro"><div><p className="eyebrow">Analytics & reports</p><h1>Recorded cadastral performance</h1><p>Statistics across stored projects—not model evaluation benchmarks.</p></div><button className="action-secondary" disabled={loading} onClick={() => setRevision(x => x + 1)}>Refresh</button></div>
    {loading && <p role="status">Loading analytics…</p>}{error && <p role="alert">{error}</p>}
    {data && <><section className="stat-cards">{[["Parcels", parcels.length], ["Average confidence", metrics.averageConfidence == null ? "Unavailable" : `${(metrics.averageConfidence * 100).toFixed(1)}%`], ["Average health score", health.length ? (health.reduce((a,b) => a+b,0)/health.length).toFixed(3) : "Unavailable"], ["Pending field surveys", metrics.fieldPending]].map(([label, value]) => <article className="surface-card analytics-card" key={label}><p className="card-kicker">{label}</p><h2>{value}</h2></article>)}</section>
    <div className="dashboard-grid"><Bars title="Parcels by land-use category" values={parcels.map(p => p.land_use ?? "Unclassified")} /><Bars title="Review status" values={parcels.map(p => p.status)} /><Bars title="Boundary confidence distribution" values={parcels.map(p => p.confidence_band ?? "Not reported")} /><Bars title="Survey workflow" values={data.queue.map(q => q.status)} /></div>
    <article className="surface-card analytics-card"><h2>Export & reports</h2><p>Export the records used by these charts, including project provenance.</p><button className="action-primary" onClick={download}>Download JSON report</button></article></>}
    <article className="surface-card analytics-card"><h2>Model evaluation & trends</h2><p>mIoU, boundary accuracy, review turnaround and resolved-anomaly trends are unavailable: the backend has no evaluation or resolution history API. Confidence is not accuracy. No prototype numbers are substituted.</p></article>
  </div>;
}

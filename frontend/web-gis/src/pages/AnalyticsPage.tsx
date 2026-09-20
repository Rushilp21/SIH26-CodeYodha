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
  const maximum = Math.max(...rows.map(([, count]) => count), 1);
  return <article className="surface-card analytics-card analytics-chart"><h2>{title}</h2>{!rows.length && <p>No records available.</p>}{rows.map(([label, count]) => <div className="analytics-row" key={label}><span>{label.replace(/_/g, " ")}</span><div className="analytics-bar" aria-label={`${count} ${label}`}><span style={{ width: `${Math.max(7, count / maximum * 100)}%` }} /></div><strong>{count}</strong></div>)}</article>;
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
  return <div className="page-content analytics-page"><div className="dashboard-intro analytics-intro"><h1>Recorded cadastral performance</h1><button className="action-secondary" disabled={loading} onClick={() => setRevision(x => x + 1)}>Refresh</button></div>
    {loading && <p role="status">Loading analytics…</p>}{error && <p role="alert">{error}</p>}
    {data && <><section className="stat-cards analytics-stats">{[["Parcels", parcels.length], ["Average confidence", metrics.averageConfidence == null ? "Unavailable" : `${(metrics.averageConfidence * 100).toFixed(1)}%`], ["Average health score", health.length ? `${(health.reduce((a,b) => a+b,0)/health.length * 100).toFixed(1)}%` : "Unavailable"], ["Pending field surveys", metrics.fieldPending]].map(([label, value]) => <article className="surface-card analytics-card analytics-stat" key={label}><p className="card-kicker">{label}</p><h2>{value}</h2></article>)}</section>
    <div className="analytics-grid"><Bars title="Parcels by land-use category" values={parcels.map(p => p.land_use ?? "Unclassified")} /><Bars title="Review status" values={parcels.map(p => p.status)} /><Bars title="Boundary confidence distribution" values={parcels.map(p => p.confidence_band ?? "Not reported")} /><Bars title="Survey workflow" values={data.queue.map(q => q.status)} /></div>
    <article className="surface-card analytics-card analytics-export"><h2>Export report</h2><button className="action-primary" onClick={download}>Download JSON</button></article></>}
  </div>;
}

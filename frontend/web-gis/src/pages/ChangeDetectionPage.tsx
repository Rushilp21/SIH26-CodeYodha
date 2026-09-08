import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchChanges, fetchExplanation, fetchParcels, fetchQueue, fetchParcelHistory, fetchParcelComparison } from "../api/client";
import { changeDate, changeLabel, joinChangeEvents } from "../data/changeDetection";
import { useAsync } from "../hooks/useAsync";
import { ParcelMap } from "../map/ParcelMap";
import { Icon } from "../components/Icon";
import "../styles/change-detection.css";

export function ChangeDetectionPage() {
  const { projectId = "" } = useParams();
  return <ChangeWorkspace key={projectId} projectId={projectId} />;
}

function ChangeWorkspace({ projectId }: { projectId: string }) {
  const [revision, setRevision] = useState(0);
  const changes = useAsync(() => fetchChanges(projectId), [projectId, revision]);
  const parcels = useAsync(() => fetchParcels(projectId), [projectId, revision]);
  const survey = useAsync(() => fetchQueue(projectId), [projectId, revision]);
  const [type, setType] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("priority");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const events = useMemo(() => joinChangeEvents(changes.data ?? [], parcels.data ?? [], survey.data ?? []),
    [changes.data, parcels.data, survey.data]);
  const types = Array.from(new Set(events.map((event) => event.change.type))).sort();
  const filtered = useMemo(() => events.filter((event) =>
    (type === "all" || event.change.type === type) &&
    `${event.change.parcel_id} ${event.parcel?.land_use ?? ""}`.toLowerCase().includes(search.toLowerCase())
  ).sort((a, b) => sort === "priority"
    ? (b.queue[0]?.priority_score ?? -Infinity) - (a.queue[0]?.priority_score ?? -Infinity)
    : (Date.parse(b.change.detected_at ?? "") || 0) - (Date.parse(a.change.detected_at ?? "") || 0)),
  [events, type, search, sort]);
  const selected = filtered.find((event) => event.key === selectedKey) ?? filtered[0] ?? null;
  const selectedId = selected?.change.parcel_id;
  const history = useAsync(async () => selectedId ? fetchParcelHistory(selectedId) : null, [selectedId, revision]);
  const comparison = useAsync(async () => selectedId ? fetchParcelComparison(selectedId) : null, [selectedId, revision]);
  const oldVersion = history.data?.parcel_id === selectedId ? history.data.versions[0] : null;
  const comparisonBounds = useMemo(() => selected?.parcel ? [selected.parcel, ...(oldVersion ? [{ ...selected.parcel, geom: oldVersion.geom }] : [])] : [], [selected?.parcel, oldVersion]);
  const evidence = useAsync(async () => selectedId ? fetchExplanation(selectedId) : null, [selectedId, revision]);
  // useAsync preserves its previous result during refresh. Never show another
  // parcel's evidence while the next request is still pending or has failed.
  const explanation = !evidence.error && evidence.data?.parcel_id === selectedId ? evidence.data : null;
  const mapParcels = useMemo(() => {
    const ids = new Set(filtered.map((event) => event.change.parcel_id));
    return (parcels.data ?? []).filter((parcel) => ids.has(parcel.id));
  }, [filtered, parcels.data]);
  const boundary = explanation?.components.filter((item) => item.component === "deviation_from_baseline" || item.component === "edge_alignment");

  return <div className="changes-workspace">
    <aside className="changes-list">
      <header className="changes-list-header">
        <Link to={`/projects/${projectId}`} className="back-link">← Map workspace</Link>
        <h1>Detected changes <span className="badge badge-primary">{filtered.length}</span></h1>
        <p>Inspect cadastral anomalies and survey priorities.</p>
        <label>Search parcels<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Parcel ID or land use" /></label>
        <div className="changes-filters">
          <label>Change type<select value={type} onChange={(event) => setType(event.target.value)}><option value="all">All types</option>{types.map((value) => <option key={value} value={value}>{changeLabel(value)}</option>)}</select></label>
          <label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="priority">Survey priority</option><option value="recent">Most recent</option></select></label>
        </div>
        <button className="action-secondary" disabled={changes.loading || parcels.loading || survey.loading} onClick={() => setRevision((value) => value + 1)}>Refresh data</button>
      </header>
      <div className="changes-events" aria-label="Detected change events">
        {changes.loading && <p role="status">Loading changes…</p>}
        {changes.error && <p role="alert">Unable to load changes: {changes.error}</p>}
        {!changes.loading && !changes.error && !filtered.length && <p>No changes match these filters.</p>}
        {!changes.error && filtered.map((event) => <button key={event.key} className={`change-event ${event.key === selected?.key ? "selected" : ""}`} onClick={() => setSelectedKey(event.key)} aria-pressed={event.key === selected?.key}>
          <span className={`change-kind kind-${event.change.type}`}><Icon name="changes" size={14} />{changeLabel(event.change.type)}</span>
          <strong>{event.change.parcel_id}</strong>
          <span>Magnitude {event.change.magnitude.toFixed(3)}</span>
          <small>{changeDate(event.change.detected_at)}</small>
          <small>{survey.error ? "Survey priority unavailable" : event.queue.length ? `Survey priority ${event.queue[0].priority_score.toFixed(2)}` : "No survey queue entry"}</small>
          {event.change.demo && <span className="adapter-label">Demo source</span>}
        </button>)}
      </div>
    </aside>

    <section className="changes-center" aria-label="Geometry comparison">
      <div className="geometry-comparison">
        <article className="current-geometry">
          <span className="comparison-label">Historical geometry</span>
          {oldVersion && selected?.parcel ? <><ParcelMap className="changes-map" fitParcels={comparisonBounds} parcels={[{ ...selected.parcel, geom: oldVersion.geom }]} selectedId={selected.parcel.id} /><div className="changes-map-key">{changeDate(oldVersion.captured_at)} · {oldVersion.source}</div></> : <div className="historical-unavailable"><Icon name="changes" size={30} /><h2>{history.loading ? "Loading history…" : "No historical boundary available"}</h2><p>{history.error ?? "No stored parcel version was returned. No baseline is invented."}</p></div>}
        </article>
        <article className="current-geometry">
          <span className="comparison-label current">Current geometry{selected?.parcel ? ` · v${selected.parcel.version}` : ""}</span>
          <ParcelMap className="changes-map" fitParcels={comparisonBounds.length ? comparisonBounds : undefined} parcels={mapParcels} selectedId={selected?.parcel?.id} onSelect={(id) => setSelectedKey(filtered.find((event) => event.change.parcel_id === id)?.key ?? null)} />
          {(parcels.loading || parcels.error || !mapParcels.length) && <div className="changes-map-message" role="status">{parcels.loading ? "Loading geometry…" : parcels.error ? `Geometry unavailable: ${parcels.error}` : "No current geometry for the selected events."}</div>}
          <div className="changes-map-key">Current parcels · blue: AI processed · amber: review · green: verified · red: rejected</div>
        </article>
      </div>
      <article className="change-evidence">
        <h2>Explainable evidence</h2>
        {!selected && <p>Select a change event to inspect its evidence.</p>}
        {selected && <>
          <div className="comparison-metrics">
            <div><span>Current recorded area</span><strong>{selected.parcel?.area_sqm == null ? "Unavailable" : `${selected.parcel.area_sqm.toLocaleString()} m²`}</strong></div>
            <div><span>Historical area / discrepancy</span><strong>{comparison.data?.historical_area_sqm == null ? "Unavailable" : `${comparison.data.historical_area_sqm.toFixed(1)} m²`}</strong><small>{comparison.error ?? (comparison.data?.area_difference_sqm == null ? "No stored comparison" : `Area change ${comparison.data.area_difference_sqm.toFixed(1)} m² (${comparison.data.area_difference_percent?.toFixed(1) ?? "n/a"}%)`)}</small></div>
            <div><span>Boundary mismatch</span><strong>{boundary?.length ? "Evidence available below" : "Not reported"}</strong><small>Anomaly magnitude is not a distance or area measurement.</small></div>
          </div>
          {comparison.data?.boundary_difference_sqm != null && <p>Boundary symmetric-difference area: {comparison.data.boundary_difference_sqm.toFixed(1)} m². {comparison.data.method}.</p>}
          {evidence.loading && <p role="status">Loading explanation…</p>}
          {evidence.error && <p role="alert">Explanation unavailable: {evidence.error}</p>}
          {explanation && <><p>{explanation.explanation}</p><div className="change-evidence-grid">{explanation.components.map((item, index) => <article key={`${item.component}-${index}`}><h3>{changeLabel(item.component)} <span>{item.score.toFixed(3)}</span></h3><p>{item.explanation}</p></article>)}</div></>}
          {!evidence.loading && !evidence.error && !explanation?.components.length && <p>No component evidence has been returned for this parcel.</p>}
        </>}
      </article>
    </section>

    <aside className="changes-summary">
      <h2>Change summary</h2><p>{filtered.length} events · {new Set(filtered.map((event) => event.change.parcel_id)).size} parcels</p>
      {types.map((value) => <div className="change-summary-row" key={value}><span>{changeLabel(value)}</span><strong>{filtered.filter((event) => event.change.type === value).length}</strong></div>)}
      <h2>Survey prioritization</h2>
      {survey.loading && <p role="status">Loading survey queue…</p>}
      {survey.error && <p role="alert">Survey queue unavailable: {survey.error}</p>}
      {!survey.loading && !survey.error && selected && (selected.queue.length ? selected.queue.map((item) => <article className="survey-priority-card" key={item.id}><strong>Priority {item.priority_score.toFixed(2)}</strong><p>{item.reason}</p><span>{changeLabel(item.status)}</span><small>Assigned to: {item.assigned_to ?? "Unassigned"}</small></article>) : <p>No survey queue entry for this parcel.</p>)}
      {selected && <div className="change-actions"><Link className="action-primary" to={`/projects/${projectId}/parcels/${selected.change.parcel_id}`}>Review parcel</Link><Link className="action-secondary" to={`/projects/${projectId}/queue?parcel=${encodeURIComponent(selected.change.parcel_id)}`}>Open survey queue</Link></div>}
    </aside>
  </div>;
}

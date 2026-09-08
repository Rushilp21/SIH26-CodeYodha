import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchChanges, fetchExplanation, fetchParcel, fetchParcels, fetchProjectStatus, verifyParcel } from "../api/client";
import { ProcessingPanel } from "../components/ProcessingPanel";
import { Icon } from "../components/Icon";
import { ParcelDetailsPanel } from "../components/ParcelDetailsPanel";
import { useAsync } from "../hooks/useAsync";
import { ParcelMap } from "../map/ParcelMap";

type StatusFilter = "all" | "ai_processed" | "needs_review" | "verified" | "rejected";

const statusLabels: Record<StatusFilter, string> = {
  all: "All", ai_processed: "AI processed", needs_review: "Needs review", verified: "Verified", rejected: "Rejected",
};

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const project = useAsync(() => fetchProjectStatus(projectId), [projectId]);
  const parcels = useAsync(() => fetchParcels(projectId), [projectId]);
  const changes = useAsync(() => fetchChanges(projectId), [projectId]);
  const [params] = useSearchParams();
  const [selectedId, setSelectedId] = useState<string | null>(params.get("parcel"));
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [showAi, setShowAi] = useState(true);
  const [showExisting, setShowExisting] = useState(true);
  const [showField, setShowField] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const selectedParcel = parcels.data?.find((parcel) => parcel.id === selectedId) ?? null;
  const explanation = useAsync(() => selectedId ? fetchExplanation(selectedId) : Promise.resolve(null), [selectedId]);
  const visibleParcels = useMemo(() => (parcels.data ?? []).filter((parcel) => {
    const includedSource = (parcel.source === "ai_extracted" && showAi) || (parcel.source === "existing_gis" && showExisting) || (parcel.source === "field_verified" && showField);
    return includedSource && (statusFilter === "all" || parcel.status === statusFilter);
  }), [parcels.data, showAi, showExisting, showField, statusFilter]);
  const selectedAnomalies = (changes.data ?? []).filter((change) => change.parcel_id === selectedId);

  async function verifySelectedParcel() {
    if (!selectedParcel) return;
    setVerifying(true);
    setFeedback(null);
    try {
      const result = await verifyParcel(selectedParcel.id);
      const updated = await fetchParcel(selectedParcel.id);
      parcels.setData((current) => current?.map((parcel) => parcel.id === updated.id ? updated : parcel) ?? null);
      setFeedback(result.message);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Verification could not be saved.");
    } finally {
      setVerifying(false);
    }
  }

  async function refreshOutputs() {
    const [nextProject, nextParcels, nextChanges] = await Promise.all([fetchProjectStatus(projectId), fetchParcels(projectId), fetchChanges(projectId)]);
    project.setData(nextProject); parcels.setData(nextParcels); changes.setData(nextChanges);
    if (selectedId) explanation.setData(await fetchExplanation(selectedId));
  }

  if (project.loading || parcels.loading) return <div className="page-content"><LoadingState label="Loading Web-GIS workspace…" /></div>;
  if (project.error || parcels.error) return <div className="page-content"><ErrorState message={project.error ?? parcels.error ?? "Unable to load project"} /></div>;

  return (
    <div className="gis-workspace">
      <aside className="map-sidebar">
        <div className="map-sidebar-header"><div><p className="card-kicker">Project workspace</p><h1>{project.data?.name ?? "Project"}</h1></div><Link to="/" className="back-link">Dashboard</Link></div>
        <div className="map-sidebar-block"><div className="project-status"><StatusBadge status={project.data?.status ?? "created"} /><span>{project.data?.parcel_count ?? 0} parcels</span></div><ProcessingPanel key={projectId} projectId={projectId} onRefresh={refreshOutputs} /></div>
        <div className="map-sidebar-block"><h2>Filter by status</h2><div className="filter-chips">{(Object.keys(statusLabels) as StatusFilter[]).map((status) => <button key={status} type="button" className={statusFilter === status ? "active" : ""} onClick={() => setStatusFilter(status)}>{statusLabels[status]}</button>)}</div></div>
        <div className="map-sidebar-block"><h2>Data layers</h2><LayerToggle label="AI parcel boundaries" checked={showAi} onChange={setShowAi} /><LayerToggle label="Existing GIS parcels" checked={showExisting} onChange={setShowExisting} /><LayerToggle label="Field-verified parcels" checked={showField} onChange={setShowField} /></div>
        <div className="map-sidebar-block"><h2>Map legend</h2><Legend color="#3B82F6" label="AI processed" /><Legend color="#F59E0B" label="Needs review" /><Legend color="#10B981" label="Verified" /><Legend color="#EF4444" label="Rejected" /></div>
        <div className="visible-count"><Icon name="map" size={15} /><strong>{visibleParcels.length}</strong><span>parcels visible</span></div>
      </aside>

      <section className="map-stage">
        <div className="map-stage-toolbar"><span><Icon name="map" size={15} /> Web-GIS parcel boundaries</span><span className="map-hint">Select a colored parcel for evidence and actions</span></div>
        <ParcelMap className="workspace-map" parcels={visibleParcels} selectedId={selectedId ?? undefined} onSelect={(id) => { setSelectedId(id); setFeedback(null); }} />
        {changes.error ? <div className="map-warning">Change-detection data unavailable: {changes.error}</div> : null}
      </section>

      <ParcelDetailsPanel projectId={projectId} parcel={selectedParcel} explanation={!explanation.error && explanation.data?.parcel_id === selectedId ? explanation.data : null} explanationError={explanation.error} explanationLoading={explanation.loading && Boolean(selectedId)} anomalies={selectedAnomalies} anomaliesLoading={changes.loading} anomaliesError={changes.error} verifying={verifying} feedback={feedback} onClose={() => { setSelectedId(null); setFeedback(null); }} onVerify={verifySelectedParcel} />
    </div>
  );
}

function LayerToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) { return <label className="layer-toggle"><span>{label}</span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><i /></label>; }
function Legend({ color, label }: { color: string; label: string }) { return <div className="map-legend-row"><i style={{ background: color }} /><span>{label}</span></div>; }

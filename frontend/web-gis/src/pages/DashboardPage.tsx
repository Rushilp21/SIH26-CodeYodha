import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchDashboardSnapshot } from "../api/client";
import { dashboardMetrics } from "../data/dashboardMetrics";
import { Icon } from "../components/Icon";
import { ImportWorkspace } from "../components/ImportWorkspace";

import { useAsync } from "../hooks/useAsync";

export function DashboardPage() {
  const [revision, setRevision] = useState(0);
  const { data, error, loading } = useAsync(fetchDashboardSnapshot, [revision]);
  const parcels = data?.parcels ?? [];
  const { verified, needsReview, fieldPending, averageConfidence } = dashboardMetrics(parcels, data?.queue ?? []);

  return (
    <div className="page-content fade-in">
      <div className="dashboard-intro">
        <div>
          <p className="eyebrow">Cadastral operations</p>
          <h1>Parcel intelligence at a glance</h1>
          <p>Counts are calculated from stored backend records; demo provenance is shown above.</p>
        </div>
        <div className="live-note">{loading ? "Loading records…" : error ? "Records unavailable" : "Backend records loaded"}</div>
        <button className="action-secondary" disabled={loading} onClick={() => setRevision(x => x + 1)}>Refresh</button>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? (
        <ErrorState message={error} />
      ) : null}
      {!loading && !error ? <>
        <ImportWorkspace />
        <section className="stat-cards" aria-label="Recorded parcel statistics">
          <StatCard icon={<Icon name="map" size={20} />} iconClass="blue" label="Total Parcels" value={parcels.length.toLocaleString()} sub={`${data?.projects.length ?? 0} projects`} />
          <StatCard icon={<Icon name="check" size={20} />} iconClass="green" label="Verified" value={verified.toLocaleString()} sub="Verified through the API" />
          <StatCard icon={<Icon name="clock" size={20} />} iconClass="amber" label="Needs Review" value={needsReview.toLocaleString()} sub="Awaiting GIS action" />
          <StatCard icon={<Icon name="alert" size={20} />} iconClass="red" label="Pending Field Surveys" value={fieldPending.toLocaleString()} sub="Unique parcels in pending / assigned queue entries" />
        </section>

        <section className="dashboard-grid">
          <div className="surface-card project-section">
            <div className="section-header">
              <div><p className="card-kicker">Workspace</p><h2>Projects</h2></div>
              <span className="badge badge-primary">{data?.projects.length ?? 0} available</span>
            </div>
            <div className="project-list">
              {data?.projects.map((project) => (
                <Link className="project-row" key={project.id} to={`/projects/${project.id}`}>
                  <div className="project-mark"><Icon name="map" size={18} /></div>
                  <div><strong>{project.name}{project.demo ? " · DEMO" : ""}</strong><span>Open map workspace and review queue</span></div>
                  <StatusBadge status={project.status} />
                  <span className="project-arrow">→</span>
                </Link>
              ))}
              {!data?.projects.length ? <p className="empty-copy">No projects have been returned by the API.</p> : null}
            </div>
          </div>

          <div className="surface-card confidence-section">
            <p className="card-kicker">Recorded quality signal</p>
            <h2>Average boundary confidence</h2>
            <div className="confidence-value"><Icon name="trend" size={22} /> {averageConfidence == null ? "n/a" : `${(averageConfidence * 100).toFixed(1)}%`}</div>
            <p>Calculated from parcel confidence scores returned by the target API.</p>
            <div className="confidence-bar"><span style={{ width: `${Math.min((averageConfidence ?? 0) * 100, 100)}%` }} /></div>
          </div>
        </section>

        <section className="surface-card activity-section">
          <div className="section-header"><div><p className="card-kicker">Activity</p><h2>Recent activity</h2></div><span className="adapter-label">Unavailable</span></div>
          <p className="panel-note">The backend does not expose an activity feed. No simulated activity is displayed.</p>
        </section>
      </> : null}
    </div>
  );
}

function StatCard({ icon, iconClass, label, value, sub }: { icon: ReactNode; iconClass: string; label: string; value: string; sub: string }) {
  return <div className="stat-card"><div className={`stat-icon ${iconClass}`}>{icon}</div><p>{label}</p><strong>{value}</strong><span>{sub}</span></div>;
}

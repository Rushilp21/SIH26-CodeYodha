import { type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchDashboardSnapshot } from "../api/client";
import { Icon } from "../components/Icon";
import { demoDashboardActivity } from "../data/dashboardAdapter";
import { useAsync } from "../hooks/useAsync";

export function DashboardPage() {
  const { data, error, loading } = useAsync(fetchDashboardSnapshot, []);
  const parcels = data?.parcels ?? [];
  const verified = parcels.filter((parcel) => parcel.status === "verified").length;
  const needsReview = parcels.filter((parcel) => parcel.status === "needs_review").length;
  const rejected = parcels.filter((parcel) => parcel.status === "rejected").length;
  const scores = parcels.flatMap((parcel) => parcel.confidence_score == null ? [] : [parcel.confidence_score]);
  const averageConfidence = scores.length ? scores.reduce((total, score) => total + score, 0) / scores.length : null;

  return (
    <div className="page-content fade-in">
      <div className="dashboard-intro">
        <div>
          <p className="eyebrow">Cadastral operations</p>
          <h1>Parcel intelligence at a glance</h1>
          <p>Live counts below are calculated from the canonical project and parcel APIs.</p>
        </div>
        <div className="live-note"><span /> Live API data</div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? (
        <ErrorState message={`API unreachable (${error}). Start backend on :8000 and seed data.`} />
      ) : null}
      {!loading && !error ? <>
        <section className="stat-cards" aria-label="Live parcel statistics">
          <StatCard icon={<Icon name="map" size={20} />} iconClass="blue" label="Total Parcels" value={parcels.length.toLocaleString()} sub={`${data?.projects.length ?? 0} active projects`} />
          <StatCard icon={<Icon name="check" size={20} />} iconClass="green" label="Verified" value={verified.toLocaleString()} sub="Verified through the API" />
          <StatCard icon={<Icon name="clock" size={20} />} iconClass="amber" label="Needs Review" value={needsReview.toLocaleString()} sub="Awaiting GIS action" />
          <StatCard icon={<Icon name="alert" size={20} />} iconClass="red" label="Rejected" value={rejected.toLocaleString()} sub="Requires follow-up" />
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
                  <div><strong>{project.name}</strong><span>Open map workspace and review queue</span></div>
                  <StatusBadge status={project.status} />
                  <span className="project-arrow">→</span>
                </Link>
              ))}
              {!data?.projects.length ? <p className="empty-copy">No projects have been returned by the API.</p> : null}
            </div>
          </div>

          <div className="surface-card confidence-section">
            <p className="card-kicker">Live quality signal</p>
            <h2>Average boundary confidence</h2>
            <div className="confidence-value"><Icon name="trend" size={22} /> {averageConfidence == null ? "n/a" : `${(averageConfidence * 100).toFixed(1)}%`}</div>
            <p>Calculated from parcel confidence scores returned by the target API.</p>
            <div className="confidence-bar"><span style={{ width: `${Math.min((averageConfidence ?? 0) * 100, 100)}%` }} /></div>
          </div>
        </section>

        <section className="surface-card activity-section">
          <div className="section-header"><div><p className="card-kicker">Activity</p><h2>Recent activity</h2></div><span className="adapter-label">Demo adapter — API unavailable</span></div>
          {demoDashboardActivity.map((activity) => <div className={`activity-item ${activity.kind}`} key={activity.id}><i /><span>{activity.message}</span><time>{activity.time}</time></div>)}
        </section>
      </> : null}
    </div>
  );
}

function StatCard({ icon, iconClass, label, value, sub }: { icon: ReactNode; iconClass: string; label: string; value: string; sub: string }) {
  return <div className="stat-card"><div className={`stat-icon ${iconClass}`}>{icon}</div><p>{label}</p><strong>{value}</strong><span>{sub}</span></div>;
}

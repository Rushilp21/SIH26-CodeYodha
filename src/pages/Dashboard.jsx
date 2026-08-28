import { useNavigate } from "react-router-dom";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts";
import {
  Map, CheckCircle, Clock, AlertTriangle,
  TrendingUp, Cpu, Users
} from "lucide-react";
import {
  dashboardStats, processingTimeline, confidenceDistribution, recentActivity
} from "../data/mockData";

const ACTIVITY_COLORS = {
  approved: "#10B981", flagged: "#F59E0B", field: "#EF4444",
  edited: "#1E5AA8", model: "#8B5CF6"
};

function StatCard({ label, value, sub, icon: Icon, iconBg, iconColor, onClick }) {
  return (
    <div className="stat-card" style={{ cursor: onClick ? "pointer" : "default" }} onClick={onClick}>
      <div className="stat-icon" style={{ background: iconBg }}>
        <Icon size={20} color={iconColor} />
      </div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

const PipelineBar = () => {
  const steps = [
    { label: "Ingested", pct: 100, color: "#10B981" },
    { label: "Segmented", pct: 96, color: "#3B82F6" },
    { label: "RL Refined", pct: 91, color: "#8B5CF6" },
    { label: "Validated", pct: 84, color: "#F59E0B" },
    { label: "Ready", pct: 78, color: "#1E5AA8" },
  ];
  return (
    <div className="card">
      <div className="card-title">AI Processing Pipeline — Current Batch</div>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        {steps.map(s => (
          <div key={s.label} style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 4, fontWeight: 600 }}>{s.pct}%</div>
            <div style={{ height: 6, background: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${s.pct}%`, height: "100%", background: s.color, borderRadius: 4, transition: "width 1s ease" }} />
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
        <Cpu size={13} style={{ color: "var(--primary)" }} />
        <span><strong style={{ color: "var(--primary)" }}>34 corrections</strong> from GIS officers improved model accuracy by <strong>+4.1%</strong> this month</span>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  return (
    <div className="page-content fade-in">
      {/* Stats */}
      <div className="stat-cards">
        <StatCard label="Total Parcels Processed" value={dashboardStats.totalParcels.toLocaleString()} sub="↑ 312 this month" icon={Map} iconBg="#EFF6FF" iconColor="#1E5AA8" />
        <StatCard label="Auto-Approved" value={`${dashboardStats.autoApproved.toLocaleString()} (${dashboardStats.autoApprovedPct}%)`} sub="No human review needed" icon={CheckCircle} iconBg="#D1FAE5" iconColor="#10B981" />
        <StatCard label="Pending Review" value={dashboardStats.pendingReview} sub="Awaiting officer action" icon={Clock} iconBg="#FEF3C7" iconColor="#F59E0B" onClick={() => navigate("/review")} />
        <StatCard label="Field Verification" value={dashboardStats.fieldVerification} sub="Requires on-site survey" icon={AlertTriangle} iconBg="#FEE2E2" iconColor="#EF4444" onClick={() => navigate("/review")} />
      </div>

      {/* Secondary stats */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <StatCard label="Model Corrections (Aug)" value={dashboardStats.modelCorrections} sub="Human-in-the-loop feedback applied" icon={Users} iconBg="#EDE9FE" iconColor="#8B5CF6" />
        <StatCard label="Avg Confidence Score" value={`${dashboardStats.avgConfidence}%`} sub="↑ 4.1% from last month" icon={TrendingUp} iconBg="#D1FAE5" iconColor="#10B981" />
      </div>

      {/* Pipeline */}
      <div style={{ marginBottom: 20 }}>
        <PipelineBar />
      </div>

      {/* Charts */}
      <div className="analytics-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">Parcels Processed Over Time</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={processingTimeline} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <Tooltip contentStyle={{ fontSize: 12, border: "1px solid #E2E8F0", borderRadius: 8 }} />
              <Line type="monotone" dataKey="count" stroke="#1E5AA8" strokeWidth={2.5} dot={{ r: 4, fill: "#1E5AA8" }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title">Confidence Score Distribution</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={confidenceDistribution} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="range" tick={{ fontSize: 10, fill: "#94A3B8" }} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <Tooltip contentStyle={{ fontSize: 12, border: "1px solid #E2E8F0", borderRadius: 8 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}
                fill="#1E5AA8"
                label={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Activity feed */}
      <div className="card">
        <div className="section-header" style={{ marginBottom: 12 }}>
          <div className="card-title" style={{ marginBottom: 0 }}>Recent Activity</div>
          <button className="btn btn-outline btn-sm" style={{ fontSize: 11 }}>View All</button>
        </div>
        {recentActivity.map(a => (
          <div key={a.id} className="activity-item">
            <div className={`activity-dot ${a.type}`} />
            <div style={{ flex: 1, fontSize: 13 }}>
              {a.parcelId && <strong style={{ color: "var(--primary)", marginRight: 6 }}>{a.parcelId}</strong>}
              {a.message}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{a.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

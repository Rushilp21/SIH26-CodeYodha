import {
  PieChart, Pie, Cell, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { Download, FileText, Map } from "lucide-react";
import { landUseBreakdown, anomaliesByZone, modelAccuracyTrend, turnaroundData, dashboardStats } from "../data/mockData";

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "white", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</div>
      ))}
    </div>
  );
};

function ExportCard({ title, desc, icon: Icon, color }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "14px", display: "flex", gap: 12, alignItems: "flex-start", cursor: "pointer", transition: "all 0.2s" }}
      onMouseEnter={e => e.currentTarget.style.borderColor = color}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}>
      <div style={{ width: 36, height: 36, borderRadius: 8, background: `${color}20`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={18} color={color} />
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{desc}</div>
      </div>
      <div style={{ marginLeft: "auto" }}>
        <button className="btn btn-outline btn-sm"><Download size={12} /> Export</button>
      </div>
    </div>
  );
}

export default function Analytics() {
  return (
    <div className="page-content fade-in">
      {/* Top KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 22 }}>
        {[
          { label: "Model mIoU Score", value: "0.81", trend: "↑ 0.03", color: "#10B981" },
          { label: "Boundary Accuracy", value: "86.2%", trend: "↑ 2.5% vs last month", color: "#1E5AA8" },
          { label: "Avg Review Time", value: "1.8 days", trend: "↓ 2.4 days saved", color: "#8B5CF6" },
          { label: "Anomalies Resolved", value: "105 / 141", trend: "74% resolution rate", color: "#F59E0B" },
        ].map(k => (
          <div key={k.label} className="card" style={{ borderTop: `3px solid ${k.color}` }}>
            <div className="stat-label">{k.label}</div>
            <div className="stat-value" style={{ fontSize: 24, color: k.color }}>{k.value}</div>
            <div className="stat-sub">{k.trend}</div>
          </div>
        ))}
      </div>

      <div className="analytics-grid">
        {/* Land use pie */}
        <div className="card">
          <div className="card-title">Parcels by Land-Use Category</div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <ResponsiveContainer width={180} height={200}>
              <PieChart>
                <Pie data={landUseBreakdown} cx="50%" cy="50%" innerRadius={48} outerRadius={80} dataKey="value" paddingAngle={2}>
                  {landUseBreakdown.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [v, n]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {landUseBreakdown.map(e => (
                <div key={e.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: e.color, flexShrink: 0 }} />
                    {e.name}
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{e.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Model accuracy */}
        <div className="card">
          <div className="card-title">Model Accuracy Trend (SegFormer + RL)</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={modelAccuracyTrend} margin={{ top: 4, right: 4, left: -14, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis yAxisId="acc" domain={[65, 90]} tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis yAxisId="iou" orientation="right" domain={[0.6, 0.85]} tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E8F0" }} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="acc" type="monotone" dataKey="accuracy" name="Accuracy (%)" stroke="#1E5AA8" strokeWidth={2.5} dot={{ r: 4 }} />
              <Line yAxisId="iou" type="monotone" dataKey="iou" name="mIoU Score" stroke="#10B981" strokeWidth={2.5} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Anomalies per zone */}
        <div className="card">
          <div className="card-title">Anomalies Detected vs Resolved — by Zone</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={anomaliesByZone} margin={{ top: 4, right: 4, left: -14, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="zone" tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <Tooltip content={<CUSTOM_TOOLTIP />} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" name="Detected" fill="#EF4444" radius={[4,4,0,0]} />
              <Bar dataKey="resolved" name="Resolved" fill="#10B981" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Review turnaround */}
        <div className="card">
          <div className="card-title">Review Turnaround Time (Weekly Average)</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={turnaroundData} margin={{ top: 4, right: 4, left: -14, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#94A3B8" }} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} unit=" d" />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E8F0" }} />
              <Line type="monotone" dataKey="avgDays" name="Avg Days" stroke="#8B5CF6" strokeWidth={2.5} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Export */}
      <div className="card" style={{ marginTop: 4 }}>
        <div className="section-header" style={{ marginBottom: 14 }}>
          <div className="section-title">Export & Reports</div>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Last generated: 2026-08-25 18:00 IST</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <ExportCard title="Full Cadastral Report" desc="PDF report of all processed parcels with confidence scores" icon={FileText} color="#1E5AA8" />
          <ExportCard title="GeoJSON Export" desc="Export all AI-generated parcel boundaries as GeoJSON" icon={Map} color="#10B981" />
          <ExportCard title="Anomaly Summary" desc="CSV report of all flagged parcels and flag reasons" icon={Download} color="#F59E0B" />
        </div>
      </div>
    </div>
  );
}

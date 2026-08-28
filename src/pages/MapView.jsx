import { useState, useEffect } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip, useMap } from "react-leaflet";
import {
  X, CheckCircle, Edit3, XCircle, PlusCircle, ChevronLeft,
  Layers, MousePointer, Ruler, Download, ZoomIn, ZoomOut, Home
} from "lucide-react";
import { parcels, CITY_CENTER } from "../data/mockData";
import { ConfidenceRing, StatusBadge, TimelineWidget, LayerToggle, PipelineIndicator } from "../components/UIComponents";

const STATUS_COLOR = {
  approved: { color: "#10B981", fill: "#10B98122", weight: 2.5 },
  review: { color: "#F59E0B", fill: "#F59E0B22", weight: 2.5 },
  field: { color: "#EF4444", fill: "#EF444422", weight: 2.5 },
};

function MapControls() {
  const map = useMap();
  return (
    <div style={{ position: "absolute", top: 12, right: 12, zIndex: 900, display: "flex", flexDirection: "column", gap: 4 }}>
      {[
        { icon: ZoomIn, action: () => map.zoomIn(), tip: "Zoom In" },
        { icon: ZoomOut, action: () => map.zoomOut(), tip: "Zoom Out" },
        { icon: Home, action: () => map.setView(CITY_CENTER, 13), tip: "Reset View" },
      ].map(({ icon: Icon, action, tip }) => (
        <button key={tip} onClick={action} className="btn btn-outline btn-icon tooltip-host"
          style={{ background: "white", boxShadow: "var(--shadow-sm)" }}>
          <Icon size={15} />
          <span className="tooltip">{tip}</span>
        </button>
      ))}
    </div>
  );
}

function ParcelDetail({ parcel, onClose }) {
  const [actionDone, setActionDone] = useState(null);
  if (!parcel) return null;
  const s = STATUS_COLOR[parcel.status];

  const handleAction = (action) => {
    setActionDone(action);
    setTimeout(() => setActionDone(null), 2000);
  };

  return (
    <div className={`map-panel${parcel ? " open" : ""}`}>
      <div className="panel-header">
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{parcel.id}</div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{parcel.surveyNo} · {parcel.ward}</div>
        </div>
        <button className="btn btn-outline btn-sm btn-icon" onClick={onClose}><X size={14} /></button>
      </div>
      <div className="panel-body">

        {/* Confidence + Status */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20, padding: "14px", background: "var(--bg)", borderRadius: "var(--radius-sm)" }}>
          <ConfidenceRing value={parcel.confidence} size={64} />
          <div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>Boundary Confidence</div>
            <StatusBadge status={parcel.status} />
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
              {parcel.status === "approved" ? "✓ Auto-approved by AI pipeline" :
               parcel.status === "review" ? "⚠ Officer review required" :
               "⛶ Field verification required"}
            </div>
          </div>
        </div>

        {/* Pipeline */}
        <div className="panel-section">
          <div className="panel-section-title">AI Processing Stage</div>
          <div style={{ overflowX: "auto" }}>
            <PipelineIndicator currentStep={parcel.status === "approved" ? "Ready for Review" : parcel.status === "review" ? "Validated" : "RL Refined"} />
          </div>
        </div>

        {/* Info */}
        <div className="panel-section">
          <div className="panel-section-title">Parcel Information</div>
          {[
            ["Land Use", parcel.landUse], ["Zone", parcel.zone],
            ["Area", `${parcel.area} m²`], ["Owner Record", parcel.owner],
            ["Last Updated", parcel.lastUpdated],
          ].map(([k, v]) => (
            <div key={k} className="info-row">
              <span className="info-label">{k}</span>
              <span className="info-value">{v}</span>
            </div>
          ))}
        </div>

        {/* Flags */}
        {parcel.flags.length > 0 && (
          <div className="panel-section">
            <div className="panel-section-title" style={{ color: "#D97706" }}>⚠ Potential Anomalies — Verification Required</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {parcel.flags.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, padding: "8px 10px", background: "#FEF3C7", borderRadius: 6, fontSize: 12, color: "#92400E" }}>
                  <span>•</span><span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="panel-section">
          <div className="panel-section-title">Survey History</div>
          <TimelineWidget history={parcel.history} />
        </div>

        {/* Actions */}
        <div className="panel-section">
          <div className="panel-section-title">Actions</div>
          {actionDone ? (
            <div style={{ padding: "10px 14px", background: "#D1FAE5", borderRadius: 8, color: "#065F46", fontSize: 13, fontWeight: 500 }}>
              ✓ Action recorded: <strong>{actionDone}</strong>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <button className="btn btn-success btn-sm" onClick={() => handleAction("Approved")}>
                <CheckCircle size={13} /> Approve
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => handleAction("Edit Boundary")}>
                <Edit3 size={13} /> Edit Boundary
              </button>
              <button className="btn btn-danger btn-sm" onClick={() => handleAction("Rejected")}>
                <XCircle size={13} /> Reject
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => handleAction("Ground Truth Added")}>
                <PlusCircle size={13} /> Ground Truth
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const LAYERS = [
  { label: "Drone Imagery", defaultOn: true },
  { label: "Orthorectified Imagery", defaultOn: false },
  { label: "AI Parcel Boundaries", defaultOn: true },
  { label: "Existing GIS Parcels", defaultOn: true },
  { label: "Building Footprints", defaultOn: false },
  { label: "Roads", defaultOn: true },
  { label: "Land-Use Classification", defaultOn: false },
  { label: "DSM / DTM", defaultOn: false },
];

export default function MapView() {
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTool, setActiveTool] = useState("select");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = statusFilter === "all" ? parcels : parcels.filter(p => p.status === statusFilter);

  return (
    <div className="map-layout">
      {/* Left layer sidebar */}
      <div className={`map-sidebar${sidebarOpen ? "" : " collapsed"}`}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600, fontSize: 13 }}>
            <Layers size={15} /> Layers
          </div>
          <button className="btn btn-outline btn-sm btn-icon" onClick={() => setSidebarOpen(false)}>
            <ChevronLeft size={14} />
          </button>
        </div>

        <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Filter by Status</div>
          {["all", "approved", "review", "field"].map(s => (
            <button key={s} className={`btn btn-sm${statusFilter === s ? " btn-primary" : " btn-outline"}`}
              style={{ marginRight: 4, marginBottom: 4, fontSize: 11 }}
              onClick={() => setStatusFilter(s)}>
              {s === "all" ? "All" : s === "approved" ? "✓ Approved" : s === "review" ? "⚠ Review" : "⛶ Field"}
            </button>
          ))}
        </div>

        <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
          <div style={{ padding: "10px 16px 6px", fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Layer Controls</div>
          {LAYERS.map(l => <LayerToggle key={l.label} label={l.label} defaultOn={l.defaultOn} />)}
        </div>

        {/* Legend */}
        <div style={{ padding: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Legend</div>
          {[
            { color: "#10B981", label: "Auto-Approved (High Confidence)" },
            { color: "#F59E0B", label: "Needs Review (Medium)" },
            { color: "#EF4444", label: "Field Verify (Low Confidence)" },
          ].map(l => (
            <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12 }}>
              <div style={{ width: 14, height: 14, borderRadius: 3, background: l.color, flexShrink: 0 }} />
              <span style={{ color: "var(--text-secondary)" }}>{l.label}</span>
            </div>
          ))}
        </div>

        {/* Parcel count */}
        <div style={{ padding: "10px 14px", margin: "0 12px 12px", background: "var(--primary-bg)", borderRadius: 8, fontSize: 12 }}>
          <div style={{ color: "var(--primary)", fontWeight: 600 }}>{filtered.length} parcels visible</div>
          <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>Click a polygon to inspect</div>
        </div>
      </div>

      {/* Map */}
      <div className="map-container">
        {/* Toolbar */}
        <div className="map-toolbar">
          {!sidebarOpen && (
            <button className="btn btn-outline btn-sm btn-icon" onClick={() => setSidebarOpen(true)} title="Show Layers">
              <Layers size={15} />
            </button>
          )}
          {[
            { id: "select", icon: MousePointer, tip: "Select" },
            { id: "measure", icon: Ruler, tip: "Measure" },
            { id: "edit", icon: Edit3, tip: "Edit Boundary" },
          ].map(({ id, icon: Icon, tip }) => (
            <button key={id} onClick={() => setActiveTool(id)}
              className={`btn btn-sm btn-icon tooltip-host${activeTool === id ? " btn-primary" : " btn-outline"}`}>
              <Icon size={15} />
              <span className="tooltip">{tip}</span>
            </button>
          ))}
          <div style={{ width: 1, height: 24, background: "var(--border)", margin: "0 2px" }} />
          <button className="btn btn-outline btn-sm btn-icon tooltip-host">
            <Download size={15} />
            <span className="tooltip">Export GeoJSON</span>
          </button>
        </div>

        <MapContainer
          center={CITY_CENTER}
          zoom={14}
          style={{ height: "100%", width: "100%" }}
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />
          <MapControls />
          {filtered.map(p => {
            const s = STATUS_COLOR[p.status];
            return (
              <Polygon
                key={p.id}
                positions={p.polygon}
                pathOptions={{
                  color: s.color,
                  fillColor: s.fill,
                  weight: selectedParcel?.id === p.id ? 4 : s.weight,
                  fillOpacity: selectedParcel?.id === p.id ? 0.35 : 0.18,
                  opacity: 0.9,
                }}
                eventHandlers={{ click: () => setSelectedParcel(p) }}
              >
                <Tooltip sticky>
                  <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                    <strong>{p.id}</strong><br />
                    {p.landUse} · {p.ward}<br />
                    Confidence: <strong>{p.confidence}%</strong>
                  </div>
                </Tooltip>
              </Polygon>
            );
          })}
        </MapContainer>

        {/* Edit mode notice */}
        {activeTool === "edit" && (
          <div style={{ position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)", zIndex: 900, background: "#1E5AA8", color: "white", padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 500 }}>
            ✏️ Edit Mode Active — Click a parcel, then drag vertices to adjust boundary
          </div>
        )}
        {activeTool === "measure" && (
          <div style={{ position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)", zIndex: 900, background: "#8B5CF6", color: "white", padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 500 }}>
            📏 Measure Mode — Click two points to measure distance
          </div>
        )}
      </div>

      {/* Right detail panel */}
      <ParcelDetail parcel={selectedParcel} onClose={() => setSelectedParcel(null)} />
    </div>
  );
}

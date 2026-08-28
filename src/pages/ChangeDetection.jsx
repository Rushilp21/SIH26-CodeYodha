import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { changeEvents, CITY_CENTER } from "../data/mockData";
import { AlertTriangle, Building, Trash2, GitCompare, Leaf } from "lucide-react";

const TYPE_ICON = {
  "New Construction": { emoji: "🏗️", cls: "change-new", color: "#10B981", icon: Building },
  "Demolition": { emoji: "💥", cls: "change-demo", color: "#EF4444", icon: Trash2 },
  "Boundary Shift": { emoji: "↔️", cls: "change-boundary", color: "#F59E0B", icon: GitCompare },
  "Land-Use Change": { emoji: "🌾", cls: "change-landuse", color: "#8B5CF6", icon: Leaf },
};

const SEV_BADGE = {
  High: "badge-danger",
  Medium: "badge-warning",
  Low: "badge-success",
};

function MapFlyTo({ target }) {
  const map = useMap();
  if (target) map.flyTo([target.lat, target.lng], 16, { duration: 1.2 });
  return null;
}

function makeMarker(color) {
  return L.divIcon({
    html: `<div style="width:14px;height:14px;background:${color};border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`,
    className: "",
    iconAnchor: [7, 7],
  });
}

export default function ChangeDetection() {
  const [selected, setSelected] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [sevFilter, setSevFilter] = useState("all");

  const filtered = changeEvents.filter(e =>
    (typeFilter === "all" || e.type === typeFilter) &&
    (sevFilter === "all" || e.severity === sevFilter)
  );

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Left list */}
      <div style={{ width: 380, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--surface)" }}>
        <div style={{ padding: "16px 16px 10px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>
            AI-Detected Changes <span className="badge badge-primary" style={{ marginLeft: 6 }}>{filtered.length}</span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <select className="select-input" style={{ flex: 1 }} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
              <option value="all">All Types</option>
              {Object.keys(TYPE_ICON).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select className="select-input" value={sevFilter} onChange={e => setSevFilter(e.target.value)}>
              {["all","High","Medium","Low"].map(s => <option key={s} value={s}>{s === "all" ? "All Severity" : s}</option>)}
            </select>
          </div>
        </div>

        <div style={{ overflowY: "auto", padding: 12 }}>
          {filtered.map(e => {
            const t = TYPE_ICON[e.type];
            return (
              <div key={e.id} className="change-card" style={{ borderColor: selected?.id === e.id ? t.color : "var(--border)", background: selected?.id === e.id ? `${t.color}10` : "white" }}
                onClick={() => setSelected(e)}>
                <div style={{ fontSize: 24, lineHeight: 1 }}>{t.emoji}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <span className={`change-type-badge ${t.cls}`}>{e.type}</span>
                    <span className={`badge ${SEV_BADGE[e.severity]}`}>{e.severity}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 3 }}>{e.parcelId}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.4 }}>{e.description}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                    {e.date} · {e.affectedArea} m² affected
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Map */}
      <div style={{ flex: 1, position: "relative" }}>
        {/* Before/After label */}
        <div style={{ position: "absolute", top: 12, left: 12, zIndex: 900, display: "flex", gap: 6 }}>
          <div style={{ background: "white", border: "1px solid var(--border)", borderRadius: 8, padding: "6px 12px", fontSize: 12, fontWeight: 600, boxShadow: "var(--shadow-sm)" }}>
            📅 2024 Survey
          </div>
          <div style={{ background: "var(--primary)", color: "white", borderRadius: 8, padding: "6px 12px", fontSize: 12, fontWeight: 600, boxShadow: "var(--shadow-sm)" }}>
            📡 2026 AI Scan
          </div>
        </div>

        {selected && (
          <div style={{ position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)", zIndex: 900, background: "white", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 18px", boxShadow: "var(--shadow)", fontSize: 13, maxWidth: 380, textAlign: "center" }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{selected.id} — {selected.type}</div>
            <div style={{ color: "var(--text-secondary)" }}>{selected.description}</div>
            <div style={{ marginTop: 8, display: "flex", gap: 8, justifyContent: "center" }}>
              <button className="btn btn-primary btn-sm">Review Parcel</button>
              <button className="btn btn-outline btn-sm">Mark Resolved</button>
            </div>
          </div>
        )}

        <MapContainer center={CITY_CENTER} zoom={13} style={{ height: "100%", width: "100%" }} zoomControl={true}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap contributors' />
          <MapFlyTo target={selected} />
          {changeEvents.map(e => {
            const t = TYPE_ICON[e.type];
            return (
              <Marker key={e.id} position={[e.lat, e.lng]} icon={makeMarker(t.color)} eventHandlers={{ click: () => setSelected(e) }}>
                <Popup>
                  <div style={{ fontSize: 13, minWidth: 200 }}>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>{e.parcelId} — {e.type}</div>
                    <div style={{ color: "#555", lineHeight: 1.4 }}>{e.description}</div>
                    <div style={{ marginTop: 4, color: "#888", fontSize: 11 }}>{e.date} · {e.affectedArea} m²</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Right stats */}
      <div style={{ width: 220, borderLeft: "1px solid var(--border)", background: "var(--bg)", padding: 16, overflow: "auto" }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Change Summary</div>
        {Object.entries(TYPE_ICON).map(([type, t]) => {
          const cnt = changeEvents.filter(e => e.type === type).length;
          const Icon = t.icon;
          return (
            <div key={type} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", background: "white", border: "1px solid var(--border)", borderRadius: 8, marginBottom: 8 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: `${t.color}20`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icon size={16} color={t.color} />
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{type}</div>
                <div style={{ fontSize: 20, fontWeight: 800 }}>{cnt}</div>
              </div>
            </div>
          );
        })}

        <div style={{ marginTop: 16, padding: "12px", background: "#FEF3C7", borderRadius: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#92400E", marginBottom: 4 }}>⚠ High Severity</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#D97706" }}>{changeEvents.filter(e=>e.severity==="High").length}</div>
          <div style={{ fontSize: 11, color: "#A16207" }}>parcels need immediate review</div>
        </div>
      </div>
    </div>
  );
}

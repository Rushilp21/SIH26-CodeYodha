import { useState, useRef, useEffect, useCallback } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip, useMap, Polyline, Marker } from "react-leaflet";
import L from "leaflet";
import { X, CheckCircle, Edit3, XCircle, PlusCircle, ChevronLeft, Layers, MousePointer, Ruler, Download, ZoomIn, ZoomOut, Home, Save, RotateCcw, AlertTriangle } from "lucide-react";
import { CITY_CENTER } from "../data/mockData";
import { useParcels } from "../context/ParcelContext";
import { ConfidenceRing, StatusBadge, TimelineWidget, LayerToggle, PipelineIndicator } from "../components/UIComponents";

const STATUS_COLOR = {
  approved: { color: "#10B981", fill: "#10B98122", weight: 2.5 },
  review:   { color: "#F59E0B", fill: "#F59E0B22", weight: 2.5 },
  field:    { color: "#EF4444", fill: "#EF444422", weight: 2.5 },
};

function MapControls() {
  const map = useMap();
  return (
    <div style={{ position:"absolute", top:12, right:12, zIndex:900, display:"flex", flexDirection:"column", gap:4 }}>
      {[
        { icon: ZoomIn,  action: () => map.zoomIn(),              tip:"Zoom In" },
        { icon: ZoomOut, action: () => map.zoomOut(),             tip:"Zoom Out" },
        { icon: Home,    action: () => map.setView(CITY_CENTER,13), tip:"Reset View" },
      ].map(({ icon:Icon, action, tip }) => (
        <button key={tip} onClick={action} className="btn btn-outline btn-icon tooltip-host"
          style={{ background:"white", boxShadow:"var(--shadow-sm)" }}>
          <Icon size={15} /><span className="tooltip">{tip}</span>
        </button>
      ))}
    </div>
  );
}

/* ── Measure tool: click 2 points, show distance ── */
function MeasureTool({ active, onResult }) {
  const map = useMap();
  const pts = useRef([]);
  const [points, setPoints] = useState([]);

  useEffect(() => {
    if (!active) { pts.current = []; setPoints([]); return; }
    const handler = (e) => {
      const next = [...pts.current, [e.latlng.lat, e.latlng.lng]];
      if (next.length > 2) { pts.current = [next[next.length-1]]; setPoints([next[next.length-1]]); return; }
      pts.current = next;
      setPoints([...next]);
      if (next.length === 2) {
        const dist = map.distance(next[0], next[1]);
        onResult(dist < 1000 ? `${dist.toFixed(1)} m` : `${(dist/1000).toFixed(3)} km`);
      }
    };
    map.on("click", handler);
    map.getContainer().style.cursor = "crosshair";
    return () => { map.off("click", handler); map.getContainer().style.cursor = ""; };
  }, [active, map, onResult]);

  if (!active || points.length === 0) return null;
  return (
    <>
      {points.length === 2 && <Polyline positions={points} pathOptions={{ color:"#8B5CF6", weight:3, dashArray:"6 4" }} />}
      {points.map((p,i) => (
        <Marker key={i} position={p} icon={L.divIcon({
          className:"",
          html:`<div style="width:10px;height:10px;border-radius:50%;background:#8B5CF6;border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,.4)"></div>`,
          iconAnchor:[5,5]
        })} />
      ))}
    </>
  );
}

/* ── Edit boundary: drag vertices ── */
function EditBoundaryTool({ parcel, active, onSave, onCancel }) {
  const map = useMap();
  const [verts, setVerts] = useState([]);
  const dragging = useRef(null);

  useEffect(() => {
    if (active && parcel) setVerts(parcel.polygon.map(([lat,lng]) => ({ lat, lng })));
    else setVerts([]);
  }, [active, parcel]);

  useEffect(() => {
    if (!active || !verts.length) return;
    const el = map.getContainer();
    const onMouseMove = (e) => {
      if (dragging.current === null) return;
      const pt = map.containerPointToLatLng(L.point(e.clientX - el.getBoundingClientRect().left, e.clientY - el.getBoundingClientRect().top));
      setVerts(v => v.map((p,i) => i === dragging.current ? { lat: pt.lat, lng: pt.lng } : p));
    };
    const onMouseUp = () => { dragging.current = null; map.dragging.enable(); };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => { window.removeEventListener("mousemove", onMouseMove); window.removeEventListener("mouseup", onMouseUp); };
  }, [active, verts.length, map]);

  const handleSave = () => {
    const poly = verts.map(v => [v.lat, v.lng]);
    // rough area calc (shoelace)
    let area = 0;
    for (let i = 0; i < poly.length; i++) {
      const j = (i+1) % poly.length;
      area += poly[i][0] * poly[j][1];
      area -= poly[j][0] * poly[i][1];
    }
    const areaM2 = Math.abs(area) * 0.5 * 111320 * 111320;
    onSave(poly, Math.round(areaM2));
  };

  if (!active || !verts.length) return null;
  const poly = verts.map(v => [v.lat, v.lng]);
  return (
    <>
      <Polygon positions={poly} pathOptions={{ color:"#3B82F6", fillColor:"#3B82F622", weight:2.5, dashArray:"8 4" }} />
      {verts.map((v,i) => (
        <Marker key={i} position={[v.lat, v.lng]} icon={L.divIcon({
          className:"",
          html:`<div style="width:14px;height:14px;border-radius:50%;background:#3B82F6;border:2px solid white;box-shadow:0 0 6px rgba(59,130,246,.6);cursor:grab"></div>`,
          iconAnchor:[7,7]
        })} eventHandlers={{
          mousedown: () => { dragging.current = i; map.dragging.disable(); }
        }} />
      ))}
      {/* save / cancel floating */}
      <div style={{ position:"absolute", bottom:56, left:"50%", transform:"translateX(-50%)", zIndex:1000, display:"flex", gap:8 }}>
        <button className="btn btn-primary btn-sm" onClick={handleSave}><Save size={13}/> Save Boundary</button>
        <button className="btn btn-outline btn-sm" onClick={onCancel}><RotateCcw size={13}/> Cancel</button>
      </div>
    </>
  );
}

/* ── Parcel action modal (reject reason / approve note) ── */
function ActionModal({ type, parcel, onConfirm, onCancel }) {
  const [note, setNote] = useState("");
  if (!parcel) return null;
  const isReject = type === "reject";
  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,.45)", zIndex:9999, display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ background:"var(--surface)", borderRadius:12, padding:28, width:380, boxShadow:"var(--shadow-xl)" }}>
        <div style={{ fontWeight:700, fontSize:16, marginBottom:8, color: isReject ? "#EF4444" : "#10B981" }}>
          {isReject ? "❌ Reject Parcel" : "✅ Approve Parcel"} — {parcel.id}
        </div>
        <div style={{ fontSize:13, color:"var(--text-secondary)", marginBottom:16 }}>
          {isReject ? "This parcel will be moved to Field Verification." : "This parcel will be marked as Approved."}
        </div>
        <textarea
          placeholder={isReject ? "Reason for rejection (optional)…" : "Approval note (optional)…"}
          value={note} onChange={e => setNote(e.target.value)}
          style={{ width:"100%", height:80, borderRadius:8, border:"1px solid var(--border)", padding:"8px 12px", fontSize:13, resize:"none", fontFamily:"inherit", background:"var(--bg)", color:"var(--text)" }}
        />
        <div style={{ display:"flex", gap:8, marginTop:12, justifyContent:"flex-end" }}>
          <button className="btn btn-outline btn-sm" onClick={onCancel}>Cancel</button>
          <button className={`btn btn-sm ${isReject ? "btn-danger" : "btn-success"}`} onClick={() => onConfirm(note)}>
            {isReject ? "Confirm Reject" : "Confirm Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}

const LAYERS = [
  { label:"Drone Imagery", defaultOn:true },
  { label:"Orthorectified Imagery", defaultOn:false },
  { label:"AI Parcel Boundaries", defaultOn:true },
  { label:"Existing GIS Parcels", defaultOn:true },
  { label:"Building Footprints", defaultOn:false },
  { label:"Roads", defaultOn:true },
  { label:"Land-Use Classification", defaultOn:false },
  { label:"DSM / DTM", defaultOn:false },
];

function ParcelDetail({ parcel, onClose, onApprove, onReject, onEditBoundary, onGroundTruth }) {
  const [flash, setFlash] = useState(null);
  useEffect(() => { setFlash(null); }, [parcel?.id]);

  if (!parcel) return null;

  const doAction = (fn, label) => {
    fn();
    setFlash(label);
    setTimeout(() => setFlash(null), 2500);
  };

  return (
    <div className={`map-panel${parcel ? " open" : ""}`}>
      <div className="panel-header">
        <div>
          <div style={{ fontWeight:700, fontSize:15 }}>{parcel.id}</div>
          <div style={{ fontSize:12, color:"var(--text-muted)" }}>{parcel.surveyNo} · {parcel.ward}</div>
        </div>
        <button className="btn btn-outline btn-sm btn-icon" onClick={onClose}><X size={14}/></button>
      </div>
      <div className="panel-body">
        <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:20, padding:14, background:"var(--bg)", borderRadius:"var(--radius-sm)" }}>
          <ConfidenceRing value={parcel.confidence} size={64}/>
          <div>
            <div style={{ fontSize:12, color:"var(--text-secondary)", marginBottom:4 }}>Boundary Confidence</div>
            <StatusBadge status={parcel.status}/>
            <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:6 }}>
              {parcel.status==="approved" ? "✓ Auto-approved by AI pipeline" : parcel.status==="review" ? "⚠ Officer review required" : "⛶ Field verification required"}
            </div>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-section-title">AI Processing Stage</div>
          <div style={{ overflowX:"auto" }}>
            <PipelineIndicator currentStep={parcel.status==="approved" ? "Ready for Review" : parcel.status==="review" ? "Validated" : "RL Refined"}/>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-section-title">Parcel Information</div>
          {[["Land Use",parcel.landUse],["Zone",parcel.zone],["Area",`${parcel.area} m²`],["Owner Record",parcel.owner],["Last Updated",parcel.lastUpdated]].map(([k,v]) => (
            <div key={k} className="info-row"><span className="info-label">{k}</span><span className="info-value">{v}</span></div>
          ))}
        </div>

        {parcel.flags.length > 0 && (
          <div className="panel-section">
            <div className="panel-section-title" style={{ color:"#D97706" }}>⚠ Potential Anomalies</div>
            <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
              {parcel.flags.map((f,i) => (
                <div key={i} style={{ display:"flex", gap:8, padding:"8px 10px", background:"#FEF3C7", borderRadius:6, fontSize:12, color:"#92400E" }}>
                  <span>•</span><span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="panel-section">
          <div className="panel-section-title">Survey History</div>
          <TimelineWidget history={parcel.history}/>
        </div>

        <div className="panel-section">
          <div className="panel-section-title">Actions</div>
          {flash ? (
            <div style={{ padding:"10px 14px", background:"#D1FAE5", borderRadius:8, color:"#065F46", fontSize:13, fontWeight:500, display:"flex", alignItems:"center", gap:8 }}>
              <CheckCircle size={15}/> {flash}
            </div>
          ) : (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
              <button className="btn btn-success btn-sm" onClick={onApprove} disabled={parcel.status==="approved"}>
                <CheckCircle size={13}/> Approve
              </button>
              <button className="btn btn-outline btn-sm" onClick={onEditBoundary}>
                <Edit3 size={13}/> Edit Boundary
              </button>
              <button className="btn btn-danger btn-sm" onClick={onReject} disabled={parcel.status==="field"}>
                <XCircle size={13}/> Reject
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => doAction(() => onGroundTruth(), "Ground Truth Submitted")}>
                <PlusCircle size={13}/> Ground Truth
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MapView() {
  const { parcels, approveParcel, rejectParcel, editBoundary, addGroundTruth } = useParcels();
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTool, setActiveTool] = useState("select");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modal, setModal] = useState(null); // { type: 'approve'|'reject', parcel }
  const [editingParcel, setEditingParcel] = useState(null);
  const [measureResult, setMeasureResult] = useState(null);

  // Keep selectedParcel in sync when global state updates
  useEffect(() => {
    if (selectedParcel) {
      const updated = parcels.find(p => p.id === selectedParcel.id);
      if (updated) setSelectedParcel(updated);
    }
  }, [parcels]);

  const filtered = statusFilter === "all" ? parcels : parcels.filter(p => p.status === statusFilter);

  const handleApprove = () => setModal({ type:"approve", parcel: selectedParcel });
  const handleReject  = () => setModal({ type:"reject",  parcel: selectedParcel });

  const confirmModal = (note) => {
    if (modal.type === "approve") approveParcel(modal.parcel.id, note);
    else rejectParcel(modal.parcel.id, note);
    setModal(null);
  };

  const handleEditBoundary = () => {
    setEditingParcel(selectedParcel);
    setActiveTool("edit");
    setSelectedParcel(null);
  };

  const handleSaveBoundary = (newPoly, newArea) => {
    editBoundary(editingParcel.id, newPoly, newArea);
    setEditingParcel(null);
    setActiveTool("select");
  };

  const handleMeasureResult = useCallback((dist) => {
    setMeasureResult(dist);
    setTimeout(() => setMeasureResult(null), 5000);
  }, []);

  return (
    <div className="map-layout">
      {/* Modals */}
      {modal && (
        <ActionModal type={modal.type} parcel={modal.parcel}
          onConfirm={confirmModal} onCancel={() => setModal(null)}/>
      )}

      {/* Left sidebar */}
      <div className={`map-sidebar${sidebarOpen ? "" : " collapsed"}`}>
        <div style={{ padding:"12px 16px", borderBottom:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ display:"flex", alignItems:"center", gap:6, fontWeight:600, fontSize:13 }}><Layers size={15}/> Layers</div>
          <button className="btn btn-outline btn-sm btn-icon" onClick={() => setSidebarOpen(false)}><ChevronLeft size={14}/></button>
        </div>

        <div style={{ padding:"10px 16px", borderBottom:"1px solid var(--border)" }}>
          <div style={{ fontSize:11, fontWeight:700, color:"var(--text-muted)", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:6 }}>Filter by Status</div>
          {["all","approved","review","field"].map(s => (
            <button key={s} className={`btn btn-sm${statusFilter===s ? " btn-primary" : " btn-outline"}`}
              style={{ marginRight:4, marginBottom:4, fontSize:11 }}
              onClick={() => setStatusFilter(s)}>
              {s==="all" ? "All" : s==="approved" ? "✓ Approved" : s==="review" ? "⚠ Review" : "⛶ Field"}
            </button>
          ))}
        </div>

        <div style={{ borderBottom:"1px solid var(--border)", paddingBottom:4 }}>
          <div style={{ padding:"10px 16px 6px", fontSize:11, fontWeight:700, color:"var(--text-muted)", textTransform:"uppercase", letterSpacing:"0.06em" }}>Layer Controls</div>
          {LAYERS.map(l => <LayerToggle key={l.label} label={l.label} defaultOn={l.defaultOn}/>)}
        </div>

        <div style={{ padding:14 }}>
          <div style={{ fontSize:11, fontWeight:700, color:"var(--text-muted)", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:8 }}>Legend</div>
          {[{ color:"#10B981", label:"Auto-Approved (High Confidence)" }, { color:"#F59E0B", label:"Needs Review (Medium)" }, { color:"#EF4444", label:"Field Verify (Low Confidence)" }].map(l => (
            <div key={l.label} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6, fontSize:12 }}>
              <div style={{ width:14, height:14, borderRadius:3, background:l.color, flexShrink:0 }}/><span style={{ color:"var(--text-secondary)" }}>{l.label}</span>
            </div>
          ))}
        </div>

        <div style={{ padding:"10px 14px", margin:"0 12px 12px", background:"var(--primary-bg)", borderRadius:8, fontSize:12 }}>
          <div style={{ color:"var(--primary)", fontWeight:600 }}>{filtered.length} parcels visible</div>
          <div style={{ color:"var(--text-muted)", fontSize:11, marginTop:2 }}>Click a polygon to inspect</div>
        </div>
      </div>

      {/* Map */}
      <div className="map-container">
        {/* Toolbar */}
        <div className="map-toolbar">
          {!sidebarOpen && (
            <button className="btn btn-outline btn-sm btn-icon" onClick={() => setSidebarOpen(true)} title="Show Layers"><Layers size={15}/></button>
          )}
          {[
            { id:"select",  icon:MousePointer, tip:"Select Tool" },
            { id:"measure", icon:Ruler,        tip:"Measure Distance" },
            { id:"edit",    icon:Edit3,        tip:"Edit Boundary" },
          ].map(({ id, icon:Icon, tip }) => (
            <button key={id} onClick={() => {
              setActiveTool(id);
              if (id !== "edit") setEditingParcel(null);
              if (id !== "measure") setMeasureResult(null);
            }}
              className={`btn btn-sm btn-icon tooltip-host${activeTool===id ? " btn-primary" : " btn-outline"}`}>
              <Icon size={15}/><span className="tooltip">{tip}</span>
            </button>
          ))}
          <div style={{ width:1, height:24, background:"var(--border)", margin:"0 2px" }}/>
          <button className="btn btn-outline btn-sm btn-icon tooltip-host">
            <Download size={15}/><span className="tooltip">Export GeoJSON</span>
          </button>
          {activeTool === "edit" && !editingParcel && (
            <span style={{ fontSize:12, color:"#3B82F6", marginLeft:8, fontWeight:500 }}>← Select a parcel then click Edit Boundary in the panel</span>
          )}
          {activeTool === "edit" && editingParcel && (
            <span style={{ fontSize:12, color:"#3B82F6", marginLeft:8, fontWeight:500 }}>✏️ Editing: {editingParcel.id} — drag vertex handles</span>
          )}
          {measureResult && (
            <span style={{ fontSize:12, color:"#8B5CF6", marginLeft:8, fontWeight:600, background:"#F3E8FF", padding:"2px 10px", borderRadius:20 }}>📏 {measureResult}</span>
          )}
        </div>

        <MapContainer center={CITY_CENTER} zoom={14} style={{ height:"100%", width:"100%" }} zoomControl={false}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors"/>
          <MapControls/>
          <MeasureTool active={activeTool==="measure"} onResult={handleMeasureResult}/>
          <EditBoundaryTool parcel={editingParcel} active={activeTool==="edit" && !!editingParcel}
            onSave={handleSaveBoundary} onCancel={() => { setEditingParcel(null); setActiveTool("select"); }}/>
          {filtered.map(p => {
            const s = STATUS_COLOR[p.status];
            const isEditing = editingParcel?.id === p.id;
            if (isEditing) return null; // rendered by EditBoundaryTool
            return (
              <Polygon key={p.id} positions={p.polygon}
                pathOptions={{ color:s.color, fillColor:s.fill, weight:selectedParcel?.id===p.id ? 4 : s.weight, fillOpacity:selectedParcel?.id===p.id ? 0.35 : 0.18, opacity:0.9 }}
                eventHandlers={{ click: () => { if (activeTool==="select") setSelectedParcel(p); } }}>
                <Tooltip sticky>
                  <div style={{ fontSize:12, lineHeight:1.6 }}>
                    <strong>{p.id}</strong><br/>{p.landUse} · {p.ward}<br/>Confidence: <strong>{p.confidence}%</strong>
                  </div>
                </Tooltip>
              </Polygon>
            );
          })}
        </MapContainer>

        {/* Status bar */}
        {activeTool==="measure" && !measureResult && (
          <div style={{ position:"absolute", bottom:12, left:"50%", transform:"translateX(-50%)", zIndex:900, background:"#8B5CF6", color:"white", padding:"6px 16px", borderRadius:20, fontSize:12, fontWeight:500 }}>
            📏 Measure Mode — Click two points to measure distance
          </div>
        )}
        {activeTool==="edit" && !editingParcel && (
          <div style={{ position:"absolute", bottom:12, left:"50%", transform:"translateX(-50%)", zIndex:900, background:"#1E5AA8", color:"white", padding:"6px 16px", borderRadius:20, fontSize:12, fontWeight:500 }}>
            ✏️ Edit Mode — Select a parcel and click &ldquo;Edit Boundary&rdquo; in the panel
          </div>
        )}
      </div>

      {/* Right panel */}
      <ParcelDetail
        parcel={selectedParcel}
        onClose={() => setSelectedParcel(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        onEditBoundary={handleEditBoundary}
        onGroundTruth={() => addGroundTruth(selectedParcel.id)}
      />
    </div>
  );
}

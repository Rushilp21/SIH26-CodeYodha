import { useState, useMemo } from "react";
import { Search, ChevronUp, ChevronDown, CheckCircle, Edit3, XCircle, PlusCircle, X, AlertTriangle } from "lucide-react";
import { useParcels } from "../context/ParcelContext";
import { ConfidenceRing, StatusBadge, PriorityBadge, TimelineWidget, PipelineIndicator } from "../components/UIComponents";

const TABS = [
  { key:"review",   label:"Review Required" },
  { key:"field",    label:"Field Verification" },
  { key:"approved", label:"Auto-Approved" },
];

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

function DetailPanel({ parcel, onClose, onApprove, onReject, onGroundTruth }) {
  const [flash, setFlash] = useState(null);

  // Reset flash when parcel changes
  useMemo(() => { setFlash(null); }, [parcel?.id]);

  if (!parcel) return (
    <div style={{ width:360, borderLeft:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", background:"var(--bg)" }}>
      <div className="empty-state">
        <span style={{ fontSize:40 }}>🗂️</span>
        <p>Select a row to inspect parcel details</p>
      </div>
    </div>
  );

  return (
    <div style={{ width:360, borderLeft:"1px solid var(--border)", overflowY:"auto", background:"var(--surface)", flexShrink:0 }}>
      <div className="panel-header">
        <div>
          <div style={{ fontWeight:700, fontSize:15 }}>{parcel.id}</div>
          <div style={{ fontSize:12, color:"var(--text-muted)" }}>{parcel.surveyNo} · {parcel.ward}</div>
        </div>
        <button className="btn btn-outline btn-sm btn-icon" onClick={onClose}><X size={14}/></button>
      </div>
      <div className="panel-body">
        <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:18, padding:12, background:"var(--bg)", borderRadius:8 }}>
          <ConfidenceRing value={parcel.confidence} size={60}/>
          <div>
            <StatusBadge status={parcel.status}/>
            <div style={{ marginTop:4 }}><PriorityBadge priority={parcel.priority}/></div>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-section-title">AI Processing Stage</div>
          <div style={{ overflowX:"auto" }}>
            <PipelineIndicator currentStep={parcel.status==="approved" ? "Ready for Review" : parcel.status==="review" ? "Validated" : "RL Refined"}/>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-section-title">Parcel Details</div>
          {[["Land Use",parcel.landUse],["Zone",parcel.zone],["Area",`${parcel.area} m²`],["Owner",parcel.owner],["Last Updated",parcel.lastUpdated]].map(([k,v]) => (
            <div key={k} className="info-row"><span className="info-label">{k}</span><span className="info-value">{v}</span></div>
          ))}
        </div>

        {parcel.flags.length > 0 && (
          <div className="panel-section">
            <div className="panel-section-title" style={{ color:"#D97706" }}>⚠ Potential Anomalies</div>
            {parcel.flags.map((f,i) => (
              <div key={i} style={{ padding:"7px 10px", background:"#FEF3C7", borderRadius:6, fontSize:12, color:"#92400E", marginBottom:6 }}>• {f}</div>
            ))}
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
              <button className="btn btn-outline btn-sm" onClick={() => setFlash("Edit queued — open Map View to edit boundary")}>
                <Edit3 size={13}/> Edit Boundary
              </button>
              <button className="btn btn-danger btn-sm" onClick={onReject} disabled={parcel.status==="field"}>
                <XCircle size={13}/> Reject
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => { onGroundTruth(); setFlash("Ground Truth Submitted ✓"); }}>
                <PlusCircle size={13}/> Ground Truth
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReviewQueue() {
  const { parcels, approveParcel, rejectParcel, addGroundTruth } = useParcels();
  const [activeTab, setActiveTab] = useState("review");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("confidence");
  const [sortDir, setSortDir] = useState("asc");
  const [landUseFilter, setLandUseFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [modal, setModal] = useState(null);

  // Keep selected panel in sync with global state
  const selectedLive = useMemo(() =>
    selected ? parcels.find(p => p.id === selected.id) || null : null,
  [selected, parcels]);

  const tabParcels = useMemo(() => parcels.filter(p => p.status === activeTab), [parcels, activeTab]);
  const landUses = ["all", ...new Set(tabParcels.map(p => p.landUse))];

  const filtered = useMemo(() => {
    let list = tabParcels;
    if (search) list = list.filter(p => p.id.toLowerCase().includes(search.toLowerCase()) || p.ward.toLowerCase().includes(search.toLowerCase()));
    if (landUseFilter !== "all") list = list.filter(p => p.landUse === landUseFilter);
    if (priorityFilter !== "all") list = list.filter(p => p.priority === priorityFilter);
    return [...list].sort((a,b) => {
      const av = sortKey==="confidence" ? a.confidence : sortKey==="area" ? a.area : a.id;
      const bv = sortKey==="confidence" ? b.confidence : sortKey==="area" ? b.area : b.id;
      return sortDir==="asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
    });
  }, [tabParcels, search, landUseFilter, priorityFilter, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey===key) setSortDir(d => d==="asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };
  const SortIcon = ({ k }) => sortKey===k ? (sortDir==="asc" ? <ChevronUp size={12}/> : <ChevronDown size={12}/>) : null;

  const counts = {
    review:   parcels.filter(p => p.status==="review").length,
    field:    parcels.filter(p => p.status==="field").length,
    approved: parcels.filter(p => p.status==="approved").length,
  };

  const handleApprove = () => setModal({ type:"approve", parcel: selectedLive });
  const handleReject  = () => setModal({ type:"reject",  parcel: selectedLive });

  const confirmModal = (note) => {
    if (modal.type==="approve") approveParcel(modal.parcel.id, note);
    else rejectParcel(modal.parcel.id, note);
    setModal(null);
    // If parcel moved out of current tab, deselect
    const newStatus = modal.type==="approve" ? "approved" : "field";
    if (newStatus !== activeTab) setSelected(null);
  };

  return (
    <div style={{ display:"flex", height:"100%", overflow:"hidden" }}>
      {modal && (
        <ActionModal type={modal.type} parcel={modal.parcel} onConfirm={confirmModal} onCancel={() => setModal(null)}/>
      )}

      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
        <div className="page-content fade-in" style={{ paddingBottom:0, overflow:"hidden", display:"flex", flexDirection:"column", height:"100%" }}>
          {/* Tabs */}
          <div className="tabs">
            {TABS.map(t => (
              <div key={t.key} className={`tab${activeTab===t.key ? " active" : ""}`}
                onClick={() => { setActiveTab(t.key); setSelected(null); }}>
                {t.label} <span className="tab-count">{counts[t.key]}</span>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="filter-bar">
            <div className="search-input">
              <Search size={14} style={{ color:"var(--text-muted)", flexShrink:0 }}/>
              <input placeholder="Search parcel ID or ward…" value={search} onChange={e => setSearch(e.target.value)}/>
            </div>
            <select className="select-input" value={landUseFilter} onChange={e => setLandUseFilter(e.target.value)}>
              {landUses.map(l => <option key={l} value={l}>{l==="all" ? "All Land Use" : l}</option>)}
            </select>
            <select className="select-input" value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
              {["all","High","Medium","Low"].map(p => <option key={p} value={p}>{p==="all" ? "All Priority" : p+" Priority"}</option>)}
            </select>
            <div style={{ fontSize:12, color:"var(--text-muted)", whiteSpace:"nowrap" }}>{filtered.length} parcels</div>
          </div>

          {/* Table */}
          <div style={{ flex:1, overflow:"auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ cursor:"pointer" }} onClick={() => toggleSort("id")}>Parcel ID <SortIcon k="id"/></th>
                  <th style={{ cursor:"pointer" }} onClick={() => toggleSort("confidence")}>Confidence <SortIcon k="confidence"/></th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Land Use</th>
                  <th>Ward / Zone</th>
                  <th style={{ cursor:"pointer" }} onClick={() => toggleSort("area")}>Area <SortIcon k="area"/></th>
                  <th>Flag Reason</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr><td colSpan={10}><div className="empty-state"><span style={{ fontSize:32 }}>🔍</span><p>No parcels match your filter</p></div></td></tr>
                )}
                {filtered.map(p => (
                  <tr key={p.id} style={{ cursor:"pointer", background: selected?.id===p.id ? "var(--primary-bg)" : "" }}
                    onClick={() => setSelected(p)}>
                    <td><strong style={{ color:"var(--primary)" }}>{p.id}</strong></td>
                    <td><ConfidenceRing value={p.confidence} size={36}/></td>
                    <td><StatusBadge status={p.status}/></td>
                    <td><PriorityBadge priority={p.priority}/></td>
                    <td>{p.landUse}</td>
                    <td style={{ fontSize:12, color:"var(--text-secondary)" }}>{p.ward}</td>
                    <td style={{ fontSize:12 }}>{p.area} m²</td>
                    <td>
                      {p.flags.length > 0 ? (
                        <span style={{ fontSize:11, color:"#92400E", background:"#FEF3C7", padding:"2px 8px", borderRadius:12 }}>
                          {p.flags[0].length > 28 ? p.flags[0].slice(0,28)+"…" : p.flags[0]}
                        </span>
                      ) : <span style={{ color:"var(--text-muted)", fontSize:12 }}>—</span>}
                    </td>
                    <td style={{ fontSize:12, color:"var(--text-muted)" }}>{p.lastUpdated}</td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display:"flex", gap:4 }}>
                        <button className="btn btn-success btn-sm btn-icon tooltip-host" disabled={p.status==="approved"}
                          onClick={() => { setSelected(p); setModal({ type:"approve", parcel:p }); }}
                          title="Approve">
                          <CheckCircle size={13}/>
                          <span className="tooltip">Approve</span>
                        </button>
                        <button className="btn btn-danger btn-sm btn-icon tooltip-host" disabled={p.status==="field"}
                          onClick={() => { setSelected(p); setModal({ type:"reject", parcel:p }); }}
                          title="Reject">
                          <XCircle size={13}/>
                          <span className="tooltip">Reject</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Detail panel */}
      <DetailPanel
        parcel={selectedLive}
        onClose={() => setSelected(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        onGroundTruth={() => selectedLive && addGroundTruth(selectedLive.id)}
      />
    </div>
  );
}

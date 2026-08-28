import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Map, ClipboardList, GitCompareArrows,
  BarChart3, ChevronLeft, ChevronRight, Bell, LogOut, User, Cpu
} from "lucide-react";

const NAV = [
  { path: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { path: "/map", icon: Map, label: "GIS Map View" },
  { path: "/review", icon: ClipboardList, label: "Review Queue" },
  { path: "/changes", icon: GitCompareArrows, label: "Change Detection" },
  { path: "/analytics", icon: BarChart3, label: "Analytics" },
];

const PAGE_TITLES = {
  "/dashboard": "Overview Dashboard",
  "/map": "Web-GIS Map View",
  "/review": "Review Prioritization Queue",
  "/changes": "Change Detection",
  "/analytics": "Analytics & Reports",
};

export default function Shell({ children, onLogout }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">GIS</div>
          {!collapsed && (
            <div className="logo-text">
              ParcelAI
              <span>Urban Cadastral Platform</span>
            </div>
          )}
        </div>
        <nav className="sidebar-nav">
          {NAV.map(({ path, icon: Icon, label }) => (
            <div
              key={path}
              className={`nav-item${pathname === path ? " active" : ""}`}
              onClick={() => navigate(path)}
              title={collapsed ? label : ""}
            >
              <Icon className="nav-icon" size={18} />
              {!collapsed && <span>{label}</span>}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="collapse-btn" onClick={() => setCollapsed(c => !c)}>
            {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="main-area">
        <header className="topbar">
          <div>
            <div className="topbar-title">{PAGE_TITLES[pathname] || "ParcelAI"}</div>
            <div className="topbar-breadcrumb">SIH26012 · AI Urban Parcel Mapping</div>
          </div>
          <div className="topbar-spacer" />
          {/* Pipeline indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 12 }}>
            <Cpu size={14} style={{ color: "var(--primary)" }} />
            <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>Model v2.4</span>
            <span className="badge badge-success" style={{ fontSize: 10 }}>● Live</span>
          </div>
          <button className="btn btn-outline btn-sm btn-icon tooltip-host" style={{ marginRight: 4 }}>
            <Bell size={16} />
            <span className="tooltip">Notifications</span>
          </button>
          <button className="btn btn-outline btn-sm btn-icon tooltip-host" style={{ marginRight: 4 }}>
            <User size={16} />
            <span className="tooltip">Profile</span>
          </button>
          <button className="btn btn-outline btn-sm btn-icon tooltip-host" onClick={onLogout}>
            <LogOut size={16} />
            <span className="tooltip">Logout</span>
          </button>
        </header>
        <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {children}
        </main>
      </div>
    </div>
  );
}

import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { Icon } from "./Icon";
import { BackendStatus } from "./BackendStatus";
import { fetchProjects } from "../api/client";
import { useAsync } from "../hooks/useAsync";

type AppShellProps = { children: ReactNode };

function projectIdFromPath(pathname: string): string | null {
  return pathname.match(/^\/projects\/([^/]+)/)?.[1] ?? null;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const projects = useAsync(fetchProjects, [pathname]);
  const [chosen, setChosen] = useState<string | null>(null);
  const projectId = projectIdFromPath(pathname) ?? (projects.data?.some(p => p.id === chosen) ? chosen : projects.data?.[0]?.id) ?? null;
  const projectPath = projectId ? `/projects/${projectId}` : null;
  const title = pathname === "/"
    ? "Overview Dashboard"
    : pathname.includes("/analytics") ? "Analytics & Reports" : pathname.includes("/changes") ? "Change Detection" : pathname.includes("/queue")
      ? "Review Prioritization Queue"
      : pathname.includes("/parcels/")
        ? "Parcel Review"
        : "Web-GIS Map View";

  const navItems = [
    { label: "Dashboard", to: "/", icon: "dashboard" as const, enabled: true },
    { label: "GIS Map View", to: projectPath, icon: "map" as const, enabled: Boolean(projectPath) },
    { label: "Review Queue", to: projectPath ? `${projectPath}/queue` : null, icon: "queue" as const, enabled: Boolean(projectPath) },
    { label: "Change Detection", to: projectPath ? `${projectPath}/changes` : null, icon: "changes" as const, enabled: Boolean(projectPath) },
    { label: "Analytics", to: "/analytics", icon: "analytics" as const, enabled: true },
  ];

  return (
    <div className="app-shell">
      <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">GIS</div>
          {!collapsed && <div className="logo-text">BhumiSetu<span>Urban Cadastral Platform</span></div>}
        </div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map(({ label, to, icon, enabled }) =>
            enabled && to ? (
              <NavLink
                key={label}
                to={to}
                end={to === "/" || to === projectPath}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                title={collapsed ? label : undefined}
              >
                <Icon name={icon} className="nav-icon" size={18} />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            ) : (
              <div key={label} className="nav-item disabled" title="Load or create a project to open this section">
                <Icon name={icon} className="nav-icon" size={18} />
                {!collapsed && <span>{label}<small>Select project</small></span>}
              </div>
            )
          )}
        </nav>
        <div className="sidebar-footer">
          <button className="collapse-btn" type="button" onClick={() => setCollapsed((value) => !value)}>
            {collapsed ? <Icon name="right" size={16} /> : <><Icon name="left" size={16} /><span>Collapse</span></>}
          </button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <div className="topbar-title">{title}</div>
            <div className="topbar-breadcrumb">SIH26012 · AI Urban Parcel Mapping</div>
          </div>
          <div className="topbar-spacer" />
          {!!projects.data?.length && <select aria-label="Active project" value={projectId ?? ""} onChange={e => { setChosen(e.target.value); navigate(`/projects/${e.target.value}`); }}>{projects.data.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>}
          <div className="pipeline-state" title="This frontend reads the canonical BhumiSetu API">
            <Icon name="cpu" size={14} /> <span>Backend workspace</span>
          </div>
          <button className="topbar-icon" type="button" disabled title="Notifications unavailable" aria-label="Notifications unavailable"><Icon name="bell" size={16} /></button>
          <button className="topbar-icon" type="button" disabled title="Profile unavailable" aria-label="Profile unavailable"><Icon name="user" size={16} /></button>
        </header>
        <BackendStatus projectId={projectId} />
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}

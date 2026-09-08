import { NavLink, useLocation } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { Icon } from "./Icon";

type AppShellProps = { children: ReactNode };

function projectIdFromPath(pathname: string): string | null {
  return pathname.match(/^\/projects\/([^/]+)/)?.[1] ?? null;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { pathname } = useLocation();
  const projectId = projectIdFromPath(pathname);
  const projectPath = projectId ? `/projects/${projectId}` : null;
  const title = pathname === "/"
    ? "Overview Dashboard"
    : pathname.includes("/queue")
      ? "Review Prioritization Queue"
      : pathname.includes("/parcels/")
        ? "Parcel Review"
        : "Web-GIS Map View";

  const navItems = [
    { label: "Dashboard", to: "/", icon: "dashboard" as const, enabled: true },
    { label: "GIS Map View", to: projectPath, icon: "map" as const, enabled: Boolean(projectPath) },
    { label: "Review Queue", to: projectPath ? `${projectPath}/queue` : null, icon: "queue" as const, enabled: Boolean(projectPath) },
    { label: "Change Detection", to: null, icon: "changes" as const, enabled: false },
    { label: "Analytics", to: null, icon: "analytics" as const, enabled: false },
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
                end={to === "/"}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                title={collapsed ? label : undefined}
              >
                <Icon name={icon} className="nav-icon" size={18} />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            ) : (
              <div key={label} className="nav-item disabled" title={`${label} is available in a later stage`}>
                <Icon name={icon} className="nav-icon" size={18} />
                {!collapsed && <span>{label}<small>Coming soon</small></span>}
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
          <div className="pipeline-state" title="This frontend reads the canonical BhumiSetu API">
            <Icon name="cpu" size={14} /> <span>API-backed workspace</span><span className="badge badge-success">● Active</span>
          </div>
          <button className="topbar-icon" type="button" aria-label="Notifications"><Icon name="bell" size={16} /></button>
          <button className="topbar-icon" type="button" aria-label="Profile"><Icon name="user" size={16} /></button>
        </header>
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}

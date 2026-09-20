import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { Icon } from "./Icon";
import { deleteProject, fetchProjects } from "../api/client";
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
  const [deleting, setDeleting] = useState(false);
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

  async function removeActiveProject() {
    if (!projectId || deleting) return;
    const project = projects.data?.find((item) => item.id === projectId);
    if (!project || !window.confirm(`Delete “${project.name}”? All parcels, reviews and evidence in this project will be permanently removed.`)) return;
    setDeleting(true);
    try {
      await deleteProject(projectId);
      const remaining = (projects.data ?? []).filter((item) => item.id !== projectId);
      const nextId = remaining[0]?.id ?? null;
      projects.setData(remaining);
      setChosen(nextId);
      if (pathname.startsWith(`/projects/${projectId}`)) navigate(nextId ? `/projects/${nextId}` : "/");
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Project deletion failed.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-logo">
          <div className="logo-icon"><Icon name="map" size={21} /></div>
          {!collapsed && <div className="logo-text">BhumiSetu</div>}
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
          </div>
          <div className="topbar-spacer" />
          <div className="topbar-actions">
            {!!projects.data?.length && <div className="project-switcher"><Icon name="map" size={16} /><select aria-label="Active project" value={projectId ?? ""} onChange={e => { setChosen(e.target.value); navigate(`/projects/${e.target.value}`); }}>{projects.data.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select><button className="project-delete" type="button" disabled={deleting} onClick={removeActiveProject} aria-label={`Delete ${projects.data.find(p => p.id === projectId)?.name ?? "project"}`} title="Delete project"><Icon name="trash" size={16} /></button></div>}
            <button className="topbar-icon" type="button" aria-label="Notifications" title="Notifications"><Icon name="bell" size={18} /></button>
            <button className="topbar-icon" type="button" aria-label="Profile and settings" title="Profile and settings"><Icon name="user" size={18} /></button>
          </div>
        </header>
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}

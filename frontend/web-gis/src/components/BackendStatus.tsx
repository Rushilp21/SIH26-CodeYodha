import { useAsync } from "../hooks/useAsync";
import { fetchHealth, fetchProjects, fetchProjectStatus } from "../api/client";
import { useState } from "react";

export function BackendStatus({ projectId }: { projectId: string | null }) {
  const [revision, setRevision] = useState(0);
  const health = useAsync(fetchHealth, [revision]);
  const projects = useAsync(fetchProjects, [projectId, revision]);
  const projectStatus = useAsync(() => projectId ? fetchProjectStatus(projectId) : Promise.resolve(null), [projectId, revision]);
  const relevant = projectId ? projects.data?.filter((item) => item.id === projectId) : projects.data;
  const demo = relevant?.some((item) => item.demo);
  return <div className="backend-status" role="status">
    <span>{health.loading ? "Checking API…" : health.error || health.data?.status !== "ok" ? "API unavailable" : "API reachable"}</span>
    <span>{projects.loading || projectStatus.loading ? "Checking data source…" : projects.error || projectStatus.error ? "Data source unavailable" : demo ? "Demo records present" : projectStatus.data?.pipeline_provenance ?? "Backend records · run provenance unavailable"}</span>
    <span>{projectStatus.data?.rl_evidence_parcel_count ? `RL evidence stored for ${projectStatus.data.rl_evidence_parcel_count} parcels` : "RL execution status is shown only when reported by a task."}</span>
    <button onClick={() => setRevision(x => x + 1)} disabled={health.loading || projects.loading || projectStatus.loading}>Recheck services</button>
  </div>;
}

import { Link } from "react-router-dom";
import { Card, ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchProjects } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function DashboardPage() {
  const { data, error, loading } = useAsync(fetchProjects, []);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">BhumiSetu Web-GIS</h1>
      <p className="text-sm text-slate-400">
        Select the demo project, process (seeded, not live ML), then review parcels.
      </p>
      {loading ? <LoadingState /> : null}
      {error ? (
        <ErrorState message={`API unreachable (${error}). Start backend on :8000 and seed data.`} />
      ) : null}
      <div className="grid gap-3">
        {(data ?? []).map((p) => (
          <Card key={p.id} title={p.name}>
            <div className="flex items-center justify-between text-sm">
              <StatusBadge status={p.status} />
              <Link className="text-sky-400" to={`/projects/${p.id}`}>
                Open
              </Link>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

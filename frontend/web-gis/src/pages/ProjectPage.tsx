import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchParcels, fetchProjectStatus, processProject, uploadImagery } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { ParcelMap } from "../map/ParcelMap";

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const nav = useNavigate();
  const status = useAsync(() => fetchProjectStatus(projectId), [projectId]);
  const parcels = useAsync(() => fetchParcels(projectId), [projectId]);

  return (
    <div className="space-y-4">
      <Link className="text-sm text-sky-400" to="/">
        ← Dashboard
      </Link>
      <h1 className="text-xl font-semibold">{status.data?.name ?? "Project"}</h1>
      {status.loading ? <LoadingState /> : null}
      {status.error ? <ErrorState message={status.error} /> : null}
      {status.data ? (
        <Card title="Processing status">
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge status={status.data.status} />
            <span>{status.data.parcel_count} parcels</span>
            <Button
              onClick={async () => {
                await uploadImagery(projectId);
                await processProject(projectId);
                window.location.reload();
              }}
            >
              Select data / process (demo)
            </Button>
            <Link className="text-sky-400" to={`/projects/${projectId}/queue`}>
              Review queue
            </Link>
          </div>
          <p className="mt-2 text-xs text-amber-400">
            DEMO: process does not run live ML/RL. Seeded parcels are used.
          </p>
        </Card>
      ) : null}
      {parcels.data ? (
        <ParcelMap
          parcels={parcels.data}
          onSelect={(id) => nav(`/projects/${projectId}/parcels/${id}`)}
        />
      ) : null}
    </div>
  );
}

import { Link, useParams } from "react-router-dom";
import { Card, ConfidenceBadge, ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchParcels, fetchQueue } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function ReviewQueuePage() {
  const { projectId = "" } = useParams();
  const parcels = useAsync(() => fetchParcels(projectId), [projectId]);
  const queue = useAsync(() => fetchQueue(projectId), [projectId]);

  const byConf = [...(parcels.data ?? [])].sort(
    (a, b) => (a.confidence_score ?? 1) - (b.confidence_score ?? 1)
  );

  return (
    <div className="space-y-4">
      <Link className="text-sm text-sky-400" to={`/projects/${projectId}`}>
        ← Project
      </Link>
      <h1 className="text-xl font-semibold">Review queue</h1>
      <p className="text-sm text-slate-400">Sorted by confidence (low first). Survey queue by priority.</p>
      {parcels.loading || queue.loading ? <LoadingState /> : null}
      {parcels.error ? <ErrorState message={parcels.error} /> : null}
      <Card title="Parcels">
        <ul className="space-y-2 text-sm">
          {byConf.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2">
              <Link className="text-sky-400" to={`/projects/${projectId}/parcels/${p.id}`}>
                {p.id.slice(0, 8)}… {p.land_use}
              </Link>
              <span className="flex items-center gap-2">
                <ConfidenceBadge score={p.confidence_score} />
                <StatusBadge status={p.status} />
              </span>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Survey queue">
        <ul className="space-y-2 text-sm">
          {(queue.data ?? []).map((q) => (
            <li key={q.id}>
              <Link className="text-sky-400" to={`/projects/${projectId}/parcels/${q.parcel_id}`}>
                prio {q.priority_score} — {q.reason}
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

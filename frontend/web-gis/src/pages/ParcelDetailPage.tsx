import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, Card, ConfidenceBadge, ErrorState, LoadingState, StatusBadge } from "@shared/components";
import { fetchExplanation, fetchParcel, patchParcelGeom, verifyParcel } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { ParcelMap } from "../map/ParcelMap";
import { ExplanationPanel } from "../components/ExplanationPanel";

function nudge(geom: GeoJSON.Polygon): GeoJSON.Polygon {
  const ring = geom.coordinates[0].map(([x, y], i, arr) => {
    if (i === arr.length - 1) return [x, y];
    return [x + 0.00002, y];
  });
  ring[ring.length - 1] = ring[0];
  return { type: "Polygon", coordinates: [ring] };
}

export function ParcelDetailPage() {
  const { projectId = "", parcelId = "" } = useParams();
  const parcel = useAsync(() => fetchParcel(parcelId), [parcelId]);
  const expl = useAsync(() => fetchExplanation(parcelId), [parcelId]);
  const [msg, setMsg] = useState("");

  const g = parcel.data?.geom;

  return (
    <div className="space-y-4">
      <Link className="text-sm text-sky-400" to={`/projects/${projectId}/queue`}>
        ← Queue
      </Link>
      <h1 className="text-xl font-semibold">Parcel {parcelId.slice(0, 8)}</h1>
      {parcel.loading ? <LoadingState /> : null}
      {parcel.error ? <ErrorState message={parcel.error} /> : null}
      {parcel.data ? (
        <>
          <div className="flex flex-wrap gap-3 text-sm">
            <ConfidenceBadge score={parcel.data.confidence_score} />
            <span>Health {parcel.data.health_score?.toFixed(2) ?? "n/a"}</span>
            <StatusBadge status={parcel.data.status} />
          </div>
          <ParcelMap parcels={[parcel.data]} selectedId={parcel.data.id} />
          <ExplanationPanel data={expl.data} />
          <Card title="Edit / verify">
            <p className="mb-2 text-xs text-slate-400">
              Scaffold editor: nudge east then verify. Records a correction in the API.
            </p>
            <div className="flex gap-2">
              <Button
                onClick={async () => {
                  if (!g) return;
                  const next = nudge(g as GeoJSON.Polygon);
                  await patchParcelGeom(parcelId, next as never);
                  setMsg("Boundary edited (demo nudge).");
                  window.location.reload();
                }}
              >
                Edit polygon (nudge)
              </Button>
              <Button
                onClick={async () => {
                  await verifyParcel(parcelId, g);
                  setMsg("Verified — correction saved.");
                  window.location.reload();
                }}
              >
                Verify
              </Button>
            </div>
            {msg ? <p className="mt-2 text-xs text-emerald-400">{msg}</p> : null}
          </Card>
        </>
      ) : null}
    </div>
  );
}

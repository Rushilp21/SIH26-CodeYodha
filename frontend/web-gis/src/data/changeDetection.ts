import type { Parcel, SurveyQueueItem } from "@shared/types";
import type { ChangeDetectionItem } from "../api/client";

export function changeLabel(value: string): string {
  return value.split("_").join(" ");
}

export function changeDate(value: string | null): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString();
}

export function joinChangeEvents(changes: ChangeDetectionItem[], parcels: Parcel[], queue: SurveyQueueItem[]) {
  const byId = new Map(parcels.map((parcel) => [parcel.id, parcel]));
  return changes.map((change, index) => ({
    // The existing change endpoint does not expose an anomaly ID.
    key: `${change.parcel_id}:${change.type}:${change.detected_at}:${index}`,
    change,
    parcel: byId.get(change.parcel_id) ?? null,
    queue: queue.filter((item) => item.parcel_id === change.parcel_id)
      .sort((a, b) => b.priority_score - a.priority_score),
  }));
}

// Magnitudes have type-specific meanings. Never sum them as a parcel risk score,
// interpret them as metres/m², or infer a physical shift from boundary_shift:
// the intelligence engine also emits that type for low confidence.
export function topologyErrors(changes: ChangeDetectionItem[]): ChangeDetectionItem[] {
  return changes.filter((change) => change.type === "topology_break" || change.type === "overlap");
}

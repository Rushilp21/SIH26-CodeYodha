import type { Parcel, SurveyQueueItem } from "@shared/types";

export function dashboardMetrics(parcels: Parcel[], queue: SurveyQueueItem[]) {
  const scores = parcels.flatMap((parcel) => parcel.confidence_score == null ? [] : [parcel.confidence_score]);
  return {
    total: parcels.length,
    verified: parcels.filter((parcel) => parcel.status === "verified").length,
    needsReview: parcels.filter((parcel) => parcel.status === "needs_review").length,
    fieldPending: new Set(queue.filter((item) => item.status === "pending" || item.status === "assigned").map((item) => item.parcel_id)).size,
    averageConfidence: scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : null,
  };
}

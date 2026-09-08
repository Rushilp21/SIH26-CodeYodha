/**
 * Stage-1 display-only adapter. The API has no activity/history endpoint yet,
 * so these entries are deliberately labelled as demo UI data by the dashboard.
 */
export type DashboardActivity = {
  id: string;
  kind: "system" | "review" | "pipeline";
  message: string;
  time: string;
};

export const demoDashboardActivity: readonly DashboardActivity[] = [
  { id: "demo-1", kind: "pipeline", message: "Live API metrics replace the prototype dashboard counters.", time: "Demo adapter" },
  { id: "demo-2", kind: "review", message: "Activity history will appear here when a backend audit-feed API is available.", time: "Demo adapter" },
  { id: "demo-3", kind: "system", message: "Select a project to inspect parcels and work the review queue.", time: "Demo adapter" },
];

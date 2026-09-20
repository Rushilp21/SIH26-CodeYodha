type IconName = "dashboard" | "map" | "queue" | "changes" | "analytics" | "left" | "right" | "cpu" | "bell" | "user" | "trash" | "check" | "clock" | "alert" | "trend";

const glyphs: Record<IconName, string> = {
  dashboard: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  map: "M9 5 3 7v12l6-2 6 2 6-2V5l-6 2zM9 5v12m6-8v10",
  queue: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  changes: "m8 3 4 4-4 4m8 10-4-4 4-4M4 7h8m0 10h8",
  analytics: "M4 20V10m6 10V4m6 16v-7m6 7V7",
  left: "m15 18-6-6 6-6",
  right: "m9 18 6-6-6-6",
  cpu: "M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3M7 7h10v10H7z",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 13h4",
  user: "M20 21a8 8 0 0 0-16 0m12-14a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  trash: "M4 7h16m-10 4v6m4-6v6M9 7l1-3h4l1 3m3 0-1 14H7L6 7",
  check: "m5 12 4 4L19 6",
  clock: "M12 6v6l4 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
  alert: "M12 9v4m0 4h.01M10 3 2 18a2 2 0 0 0 1.8 3h16.4A2 2 0 0 0 22 18L14 3a2 2 0 0 0-4 0",
  trend: "m4 16 6-6 4 4 6-7M14 7h6v6",
};

export function Icon({ name, size = 18, className }: { name: IconName; size?: number; className?: string }) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={glyphs[name]} /></svg>;
}

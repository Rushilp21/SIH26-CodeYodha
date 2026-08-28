import { confidenceBand, type ConfidenceBand } from "../types";

const cls: Record<ConfidenceBand, string> = {
  HIGH: "bg-emerald-700",
  MEDIUM: "bg-amber-600",
  LOW: "bg-red-700",
};

export function ConfidenceBadge({ score }: { score: number | null | undefined }) {
  const band = confidenceBand(score ?? null);
  if (band == null) return <span className="text-xs text-slate-400">n/a</span>;
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs text-white ${cls[band]}`}>
      {band} {score?.toFixed(2)}
    </span>
  );
}

const map: Record<string, string> = {
  verified: "bg-emerald-700",
  needs_review: "bg-amber-700",
  ai_processed: "bg-sky-800",
  rejected: "bg-red-800",
  pending: "bg-amber-800",
  assigned: "bg-sky-800",
  completed: "bg-emerald-800",
  review: "bg-violet-800",
  processing: "bg-sky-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs text-white ${map[status] ?? "bg-slate-600"}`}>
      {status}
    </span>
  );
}

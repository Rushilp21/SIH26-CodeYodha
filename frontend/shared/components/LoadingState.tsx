export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <p className="text-sm text-slate-400">{label}</p>;
}

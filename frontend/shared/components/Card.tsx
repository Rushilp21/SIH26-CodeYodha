import type { ReactNode } from "react";

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="rounded border border-slate-700 bg-slate-800/80 p-4">
      {title ? <h2 className="mb-2 text-sm font-semibold text-slate-200">{title}</h2> : null}
      {children}
    </div>
  );
}

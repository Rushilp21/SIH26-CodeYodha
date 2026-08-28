import { Card } from "@shared/components";
import type { Explanation } from "@shared/types";

export function ExplanationPanel({ data }: { data: Explanation | null }) {
  if (!data) return <Card title="Explanation">No evidence yet.</Card>;
  return (
    <Card title="Explanation / evidence">
      <p className="text-sm">{data.explanation}</p>
      <ul className="mt-2 space-y-1 text-xs text-slate-300">
        {data.components.map((c) => (
          <li key={c.component}>
            <strong>{c.component}</strong> {c.score.toFixed(2)} — {c.explanation}
          </li>
        ))}
      </ul>
    </Card>
  );
}

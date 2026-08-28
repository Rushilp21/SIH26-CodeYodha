export function ConfidenceRing({ value, size = 56 }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const color = value >= 85 ? "#10B981" : value >= 62 ? "#F59E0B" : "#EF4444";
  const dash = (value / 100) * circ;
  return (
    <div className="conf-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#E2E8F0" strokeWidth={5} />
        <circle
          cx={size/2} cy={size/2} r={r} fill="none" stroke={color}
          strokeWidth={5} strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round" style={{ transition: "stroke-dasharray 0.5s ease" }}
        />
      </svg>
      <span className="value" style={{ color, fontSize: size > 40 ? 12 : 10 }}>{value}%</span>
    </div>
  );
}

export function StatusBadge({ status }) {
  const map = {
    approved: ["badge-success", "✓ Approved"],
    review: ["badge-warning", "⚠ Review"],
    field: ["badge-danger", "⛶ Field Verify"],
  };
  const [cls, label] = map[status] || ["badge-gray", status];
  return <span className={`badge ${cls}`}>{label}</span>;
}

export function PriorityBadge({ priority }) {
  const cls = priority === "High" ? "priority-high" : priority === "Medium" ? "priority-medium" : "priority-low";
  return <span className={`badge ${cls}`}>{priority}</span>;
}

const STEPS = ["Ingested", "Segmented", "RL Refined", "Validated", "Ready for Review"];

export function PipelineIndicator({ currentStep }) {
  const idx = STEPS.indexOf(currentStep);
  return (
    <div className="pipeline">
      {STEPS.map((s, i) => (
        <span key={s} className={`pipeline-step${i < idx ? " done" : i === idx ? " current" : ""}`} style={{ fontSize: 11 }}>
          {i < idx ? "✓ " : ""}{s}
        </span>
      ))}
    </div>
  );
}

export function TimelineWidget({ history }) {
  return (
    <div className="timeline">
      {history.map((h, i) => (
        <div key={h.year} className="timeline-step">
          <div className={`timeline-dot${i === history.length - 1 ? " current" : " done"}`}>
            {i === history.length - 1 ? "★" : "✓"}
          </div>
          <div className="timeline-year">{h.year}</div>
          <div className="timeline-label">{h.status}</div>
          <div className="timeline-label">{h.area} m²</div>
        </div>
      ))}
    </div>
  );
}

export function LayerToggle({ label, defaultOn = true, onChange }) {
  return (
    <div className="layer-item">
      <span>{label}</span>
      <label className="toggle">
        <input type="checkbox" defaultChecked={defaultOn} onChange={e => onChange && onChange(e.target.checked)} />
        <span className="toggle-slider" />
      </label>
    </div>
  );
}

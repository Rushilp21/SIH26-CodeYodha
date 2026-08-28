import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, ErrorState, LoadingState } from "@shared/components";
import { fetchHealth } from "../api/client";

export function AdminDashboardPage() {
  const [health, setHealth] = useState<{ status: string; service: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetchHealth().then(setHealth).catch((e) => setErr(e.message));
  }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Admin / vendor</h1>
      <nav className="flex gap-3 text-sm text-sky-400">
        <Link to="/projects">Projects</Link>
        <Link to="/vendors">Vendors</Link>
        <Link to="/status">System status</Link>
      </nav>
      <Card title="API">
        {!health && !err ? <LoadingState /> : null}
        {err ? <ErrorState message={err} /> : null}
        {health ? (
          <p className="text-sm">
            {health.service} — {health.status}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

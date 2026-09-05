"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

export default function RunsListPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    apiFetch<any[]>("/runs")
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoaded(true));
  }, []);

  return (
    <AppShell>
      <div className="inbox-header">
        <div>
          <h1 className="page-title">Runs</h1>
          <p className="lede">Your meeting-to-action history.</p>
        </div>
        <Link href="/runs/new">
          <button type="button">New Run</button>
        </Link>
      </div>
      {loaded && runs.length === 0 && (
        <div className="card empty-state">
          <strong>No runs yet</strong>
          Process a meeting to see approvals land here.
          <div style={{ marginTop: "1rem" }}>
            <Link href="/runs/new">
              <button type="button">Start your first run</button>
            </Link>
          </div>
        </div>
      )}
      {runs.map((run) => (
        <div key={run.id} className="card">
          <Link href={`/runs/${run.id}`}>
            <strong>{run.account?.company || "Untitled run"}</strong>
          </Link>
          <div className="action-row" style={{ marginTop: "0.5rem" }}>
            <span className={`status-pill status-${run.status}`}>{run.status}</span>
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              {run.id.slice(0, 8)}…
            </span>
          </div>
        </div>
      ))}
    </AppShell>
  );
}

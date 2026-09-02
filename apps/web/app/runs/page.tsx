"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function RunsListPage() {
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    apiFetch<any[]>("/runs").then(setRuns).catch(() => setRuns([]));
  }, []);

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <h1>Runs</h1>
      <Link href="/runs/new"><button>New Run</button></Link>
      {runs.map((run) => (
        <div key={run.id} className="card">
          <Link href={`/runs/${run.id}`}>
            <strong>{run.account?.company || "Run"}</strong> — {run.status}
          </Link>
        </div>
      ))}
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_URL, apiFetch } from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = () => apiFetch<any>(`/runs/${runId}`).then(setRun);

  useEffect(() => {
    load();
  }, [runId]);

  const approve = async () => {
    setLoading(true);
    setError("");
    try {
      await fetch(`${API_URL}/runs/${runId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sections: { emails: true, crm: true, tasks: true, workflow: "client_followup" },
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setLoading(false);
    }
  };

  const execute = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/runs/${runId}/execute`, { method: "POST" });
      if (!res.ok) throw new Error("Execute failed");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execute failed");
    } finally {
      setLoading(false);
    }
  };

  if (!run) return <main style={{ padding: "2rem" }}>Loading...</main>;

  const pkg = run.action_package;
  const scope = pkg?.scope_report;

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "2rem" }}>
      <h1>Approval Inbox</h1>
      <p>Run: {run.id} | Status: <strong>{run.status}</strong></p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h3>Account</h3>
          <p>{run.account?.company} — {run.account?.stage}</p>
          <p>Amount: ${run.account?.amount?.toLocaleString()}</p>
        </div>
        <div className="card">
          <h3>Scope Verifier</h3>
          {scope?.flags?.length ? scope.flags.map((f: any, i: number) => (
            <div key={i} className={f.type === "OUT_OF_SCOPE" ? "flag-high" : "flag-ok"}>
              <strong>{f.type}</strong>: {f.request}
              <br /><small>&quot;{f.evidence_quote}&quot;</small>
            </div>
          )) : <p>No scope flags</p>}
        </div>
      </div>

      <div className="card">
        <h3>Summary</h3>
        <p>{pkg?.summary}</p>
      </div>

      {pkg?.emails?.map((email: any, i: number) => (
        <div key={i} className="card">
          <h3>Email ({email.mode})</h3>
          <p><strong>To:</strong> {email.to?.join(", ")}</p>
          <p><strong>Subject:</strong> {email.subject}</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>{email.body}</pre>
        </div>
      ))}

      {pkg?.crm_updates?.length > 0 && (
        <div className="card">
          <h3>CRM Updates</h3>
          {pkg.crm_updates.map((c: any, i: number) => (
            <p key={i}>{c.field} → {c.value} (confidence: {c.confidence})</p>
          ))}
        </div>
      )}

      {pkg?.tasks?.length > 0 && (
        <div className="card">
          <h3>Tasks</h3>
          {pkg.tasks.map((t: any, i: number) => (
            <p key={i}><strong>{t.summary}</strong> — {t.owner} (confidence: {t.confidence})</p>
          ))}
        </div>
      )}

      {run.execution_log && (
        <div className="card">
          <h3>Execution log</h3>
          {run.execution_log.steps?.map((s: any, i: number) => (
            <p key={i}>{s.step}: {s.success ? "OK" : "FAIL"} {s.message || s.error}</p>
          ))}
        </div>
      )}

      {error && <p style={{ color: "#f4212e" }}>{error}</p>}

      {run.status === "awaiting_approval" && (
        <button onClick={approve} disabled={loading}>Approve all</button>
      )}
      {run.status === "approved" && (
        <button onClick={execute} disabled={loading}>Execute</button>
      )}
    </main>
  );
}

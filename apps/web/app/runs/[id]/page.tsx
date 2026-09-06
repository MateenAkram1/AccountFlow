"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import {
  ApprovalDraft,
  SectionKey,
  SectionStatus,
  buildApprovedPayload,
  draftFromRun,
  hasApprovedSection,
} from "@/lib/approval";

function statusLabel(status: SectionStatus) {
  if (status === "approved") return "Approved";
  if (status === "rejected") return "Rejected";
  return "Pending review";
}

function statusClass(status: SectionStatus) {
  if (status === "approved") return "badge-approved";
  if (status === "rejected") return "badge-rejected";
  return "badge-pending";
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<any>(null);
  const [draft, setDraft] = useState<ApprovalDraft | null>(null);
  const [jiraProjects, setJiraProjects] = useState<{ key: string; name?: string }[]>([]);
  const [pipelines, setPipelines] = useState<
    { id: string; label: string; stages: { id: string; label: string }[] }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const allStages = pipelines.flatMap((p) =>
    p.stages.map((s) => ({ ...s, pipelineLabel: p.label, pipelineId: p.id }))
  );
  const stageLabel = (id: string) =>
    allStages.find((s) => s.id === id)?.label || id;

  const crmFieldOptions = [
    { id: "dealstage", label: "Deal stage" },
    { id: "amount", label: "Amount" },
    { id: "closedate", label: "Close date" },
    { id: "dealname", label: "Deal name" },
  ];

  const load = async () => {
    const data = await apiFetch<any>(`/runs/${runId}`);
    setRun(data);
    if (data.status === "awaiting_approval" || data.status === "approved") {
      const next = draftFromRun(data);
      try {
        const jp = await apiFetch<{
          projects: { key: string; name?: string }[];
          selected?: { key: string; name?: string } | null;
        }>("/integrations/jira/projects");
        setJiraProjects(jp.projects || []);
        if (!next.jiraProjectKey && jp.selected?.key) {
          next.jiraProjectKey = jp.selected.key;
        } else if (!next.jiraProjectKey && jp.projects?.length) {
          next.jiraProjectKey = jp.projects[0].key;
        }
      } catch {
        // Jira may be unavailable — tasks can still be reviewed
      }
      try {
        const pipes = await apiFetch<{
          pipelines: { id: string; label: string; stages: { id: string; label: string }[] }[];
        }>("/integrations/hubspot/pipelines");
        setPipelines(pipes.pipelines || []);
        // Normalize AI-suggested stage labels to HubSpot stage IDs when possible
        const stages = (pipes.pipelines || []).flatMap((p) => p.stages);
        next.crm_updates = next.crm_updates.map((crm) => {
          if (crm.field !== "dealstage" && crm.field !== "stage") return crm;
          const raw = (crm.value || "").trim();
          const byId = stages.find((s) => s.id === raw);
          if (byId) return { ...crm, field: "dealstage", value: byId.id };
          const norm = raw.toLowerCase().replace(/[\s_-]+/g, "");
          const byLabel = stages.find(
            (s) =>
              s.label.toLowerCase().replace(/[\s_-]+/g, "") === norm ||
              s.id.toLowerCase().replace(/[\s_-]+/g, "") === norm
          );
          if (byLabel) return { ...crm, field: "dealstage", value: byLabel.id };
          // Common aliases
          const aliases: Record<string, string[]> = {
            presentationscheduled: ["proposal", "presentation", "demo"],
            appointmentscheduled: ["discovery", "appointment"],
            qualifiedtobuy: ["qualified"],
            contractsent: ["contract"],
            closedwon: ["won", "closedwon"],
            closedlost: ["lost", "closedlost"],
          };
          for (const [stageId, keys] of Object.entries(aliases)) {
            if (keys.some((k) => norm.includes(k)) && stages.some((s) => s.id === stageId)) {
              return { ...crm, field: "dealstage", value: stageId };
            }
          }
          return { ...crm, field: "dealstage" };
        });
      } catch {
        setPipelines([]);
      }
      setDraft(next);
    }
  };

  useEffect(() => {
    load();
  }, [runId]);

  const setSectionStatus = (key: SectionKey, status: SectionStatus) => {
    setDraft((prev) =>
      prev ? { ...prev, sectionStatus: { ...prev.sectionStatus, [key]: status } } : prev
    );
  };

  const approveAll = () => {
    setDraft((prev) =>
      prev
        ? {
            ...prev,
            sectionStatus: { emails: "approved", crm: "approved", tasks: "approved" },
          }
        : prev
    );
  };

  const rejectAll = () => {
    setDraft((prev) =>
      prev
        ? {
            ...prev,
            sectionStatus: { emails: "rejected", crm: "rejected", tasks: "rejected" },
          }
        : prev
    );
  };

  const confirmSelection = async () => {
    if (!draft) return;
    if (!hasApprovedSection(draft)) {
      setError("Approve at least one section (with items selected) before confirming.");
      return;
    }
    if (draft.sectionStatus.tasks === "approved" && draft.tasks.some((t) => t.selected) && !draft.jiraProjectKey) {
      setError("Select a Jira project before approving tasks.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const workflow =
        run?.action_package?.scope_report?.flags?.some(
          (f: any) => f.recommended_workflow === "change_request"
        )
          ? "change_request"
          : "client_followup";
      const payload = buildApprovedPayload(draft, workflow);
      await apiFetch(`/runs/${runId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  };

  const execute = async () => {
    setLoading(true);
    setError("");
    try {
      await apiFetch(`/runs/${runId}/execute`, { method: "POST" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execute failed");
    } finally {
      setLoading(false);
    }
  };

  if (!run) {
    return (
      <AppShell>
        <p className="muted">Loading…</p>
      </AppShell>
    );
  }

  const pkg = run.action_package;
  const scope = pkg?.scope_report;
  const grades = run.grade_report?.results ?? [];
  const canEdit = run.status === "awaiting_approval" && draft;
  const approved = run.approved;

  return (
    <AppShell>
      <header className="inbox-header">
        <div>
          <h1 className="page-title">Approval Inbox</h1>
          <p className="lede">
            Review and edit each draft before confirming. Only approved sections will execute.
          </p>
        </div>
        <div className="run-meta">
          <span>Run: {run.id.slice(0, 8)}…</span>
          <span className={`status-pill status-${run.status}`}>{run.status}</span>
        </div>
      </header>

      <div className="grid-2">
        <div className="card">
          <h3>Account</h3>
          <p>{run.account?.company} — {run.account?.stage}</p>
          <p>Amount: ${run.account?.amount?.toLocaleString() ?? "—"}</p>
        </div>
        <div className="card">
          <h3>Scope Verifier</h3>
          {scope?.skipped ? (
            <p className="muted">Skipped — no SOW provided.</p>
          ) : scope?.flags?.length ? (
            scope.flags.map((f: any, i: number) => (
              <div key={i} className={f.type === "OUT_OF_SCOPE" ? "flag-high" : "flag-ok"}>
                <strong>{f.type}</strong>: {f.request}
                <br />
                <small>&quot;{f.evidence_quote}&quot;</small>
              </div>
            ))
          ) : (
            <p>No scope issues detected</p>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Meeting summary</h3>
        <p>{pkg?.summary}</p>
        {grades.some((g: any) => !g.passed) && (
          <div className="warning-box">
            <strong>Review suggested:</strong> some items may need edits before you approve.
            {grades
              .filter((g: any) => !g.passed)
              .map((g: any, i: number) => (
                <div key={i} className="muted">
                  {g.message}
                </div>
              ))}
          </div>
        )}
      </div>

      {canEdit && draft && (
        <>
          <section className="card section-card">
            <div className="section-head">
              <div>
                <h3>Follow-up email</h3>
                <span className={statusClass(draft.sectionStatus.emails)}>
                  {statusLabel(draft.sectionStatus.emails)}
                </span>
              </div>
              <div className="section-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSectionStatus("emails", "rejected")}
                >
                  Reject section
                </button>
                <button type="button" onClick={() => setSectionStatus("emails", "approved")}>
                  Approve section
                </button>
              </div>
            </div>
            {draft.emails.length === 0 ? (
              <p className="muted">No email drafts generated.</p>
            ) : (
              draft.emails.map((email, i) => (
                <div key={i} className="item-block">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={email.selected}
                      onChange={(e) => {
                        const next = [...draft.emails];
                        next[i] = { ...next[i], selected: e.target.checked };
                        setDraft({ ...draft, emails: next });
                      }}
                    />
                    Include this email in execute
                  </label>
                  <label>To (comma-separated)</label>
                  <input
                    value={email.toStr}
                    onChange={(e) => {
                      const next = [...draft.emails];
                      next[i] = { ...next[i], toStr: e.target.value };
                      setDraft({ ...draft, emails: next });
                    }}
                  />
                  <label>Subject</label>
                  <input
                    value={email.subject}
                    onChange={(e) => {
                      const next = [...draft.emails];
                      next[i] = { ...next[i], subject: e.target.value };
                      setDraft({ ...draft, emails: next });
                    }}
                  />
                  <label>Body</label>
                  <textarea
                    rows={8}
                    value={email.body}
                    onChange={(e) => {
                      const next = [...draft.emails];
                      next[i] = { ...next[i], body: e.target.value };
                      setDraft({ ...draft, emails: next });
                    }}
                  />
                  {email.evidence_quotes?.length > 0 && (
                    <p className="evidence muted">
                      Evidence: {email.evidence_quotes.join(" · ")}
                    </p>
                  )}
                </div>
              ))
            )}
          </section>

          <section className="card section-card">
            <div className="section-head">
              <div>
                <h3>CRM updates</h3>
                <span className={statusClass(draft.sectionStatus.crm)}>
                  {statusLabel(draft.sectionStatus.crm)}
                </span>
              </div>
              <div className="section-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSectionStatus("crm", "rejected")}
                >
                  Reject section
                </button>
                <button type="button" onClick={() => setSectionStatus("crm", "approved")}>
                  Approve section
                </button>
              </div>
            </div>
            {draft.crm_updates.length === 0 ? (
              <p className="muted">No CRM updates suggested.</p>
            ) : (
              draft.crm_updates.map((crm, i) => (
                <div key={i} className="item-block">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={crm.selected}
                      onChange={(e) => {
                        const next = [...draft.crm_updates];
                        next[i] = { ...next[i], selected: e.target.checked };
                        setDraft({ ...draft, crm_updates: next });
                      }}
                    />
                    Include this field update
                  </label>
                  <div className="grid-2-tight">
                    <div>
                      <label>Field</label>
                      <select
                        value={
                          crmFieldOptions.some((f) => f.id === crm.field)
                            ? crm.field
                            : crm.field === "stage"
                              ? "dealstage"
                              : "dealstage"
                        }
                        onChange={(e) => {
                          const next = [...draft.crm_updates];
                          const field = e.target.value;
                          let value = next[i].value;
                          if (field === "dealstage") {
                            const match = allStages.find((s) => s.id === value);
                            value = match?.id || allStages[0]?.id || value;
                          }
                          next[i] = { ...next[i], field, value };
                          setDraft({ ...draft, crm_updates: next });
                        }}
                      >
                        {crmFieldOptions.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.label}
                          </option>
                        ))}
                        {!crmFieldOptions.some((f) => f.id === crm.field) &&
                          crm.field !== "stage" && (
                            <option value={crm.field}>{crm.field}</option>
                          )}
                      </select>
                    </div>
                    <div>
                      <label>Value</label>
                      {crm.field === "dealstage" || crm.field === "stage" ? (
                        <select
                          value={
                            allStages.some((s) => s.id === crm.value)
                              ? crm.value
                              : allStages[0]?.id || crm.value
                          }
                          onChange={(e) => {
                            const next = [...draft.crm_updates];
                            next[i] = {
                              ...next[i],
                              field: "dealstage",
                              value: e.target.value,
                            };
                            setDraft({ ...draft, crm_updates: next });
                          }}
                        >
                          {allStages.map((s) => (
                            <option key={`${s.pipelineId}-${s.id}`} value={s.id}>
                              {s.label}
                              {pipelines.length > 1 ? ` (${s.pipelineLabel})` : ""}
                            </option>
                          ))}
                          {allStages.length === 0 && (
                            <option value={crm.value}>
                              {stageLabel(crm.value) || crm.value || "Loading stages…"}
                            </option>
                          )}
                        </select>
                      ) : crm.field === "amount" ? (
                        <input
                          type="number"
                          inputMode="decimal"
                          value={crm.value.replace(/[$,]/g, "")}
                          onChange={(e) => {
                            const next = [...draft.crm_updates];
                            next[i] = { ...next[i], value: e.target.value };
                            setDraft({ ...draft, crm_updates: next });
                          }}
                          placeholder="120000"
                        />
                      ) : crm.field === "closedate" ? (
                        <input
                          type="date"
                          value={crm.value.slice(0, 10)}
                          onChange={(e) => {
                            const next = [...draft.crm_updates];
                            next[i] = { ...next[i], value: e.target.value };
                            setDraft({ ...draft, crm_updates: next });
                          }}
                        />
                      ) : (
                        <input
                          value={crm.value}
                          onChange={(e) => {
                            const next = [...draft.crm_updates];
                            next[i] = { ...next[i], value: e.target.value };
                            setDraft({ ...draft, crm_updates: next });
                          }}
                        />
                      )}
                    </div>
                  </div>
                  <p className="evidence muted">
                    Evidence: &quot;{crm.evidence_quote}&quot; · confidence {crm.confidence}
                  </p>
                </div>
              ))
            )}
          </section>

          <section className="card section-card">
            <div className="section-head">
              <div>
                <h3>Tasks (Jira)</h3>
                <span className={statusClass(draft.sectionStatus.tasks)}>
                  {statusLabel(draft.sectionStatus.tasks)}
                </span>
              </div>
              <div className="section-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSectionStatus("tasks", "rejected")}
                >
                  Reject section
                </button>
                <button type="button" onClick={() => setSectionStatus("tasks", "approved")}>
                  Approve section
                </button>
              </div>
            </div>
            <label>Jira project</label>
            {jiraProjects.length > 0 ? (
              <select
                value={draft.jiraProjectKey}
                onChange={(e) => setDraft({ ...draft, jiraProjectKey: e.target.value })}
              >
                {jiraProjects.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.name || p.key} ({p.key})
                  </option>
                ))}
              </select>
            ) : (
              <p className="muted">
                No Jira projects found. Create one in Jira or open{" "}
                <a href="/connect">Connect</a> to refresh.
              </p>
            )}
            {draft.tasks.length === 0 ? (
              <p className="muted">No tasks suggested.</p>
            ) : (
              draft.tasks.map((task, i) => (
                <div key={i} className="item-block">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={task.selected}
                      onChange={(e) => {
                        const next = [...draft.tasks];
                        next[i] = { ...next[i], selected: e.target.checked };
                        setDraft({ ...draft, tasks: next });
                      }}
                    />
                    Include this task
                  </label>
                  <label>Summary</label>
                  <input
                    value={task.summary}
                    onChange={(e) => {
                      const next = [...draft.tasks];
                      next[i] = { ...next[i], summary: e.target.value };
                      setDraft({ ...draft, tasks: next });
                    }}
                  />
                  <label>Description</label>
                  <textarea
                    rows={4}
                    value={task.description}
                    onChange={(e) => {
                      const next = [...draft.tasks];
                      next[i] = { ...next[i], description: e.target.value };
                      setDraft({ ...draft, tasks: next });
                    }}
                  />
                  <div className="grid-2-tight">
                    <div>
                      <label>Owner</label>
                      <input
                        value={task.owner}
                        onChange={(e) => {
                          const next = [...draft.tasks];
                          next[i] = { ...next[i], owner: e.target.value };
                          setDraft({ ...draft, tasks: next });
                        }}
                      />
                    </div>
                    <div>
                      <label>Due date</label>
                      <input
                        value={task.due_date}
                        placeholder="e.g. Friday or 2026-03-15"
                        onChange={(e) => {
                          const next = [...draft.tasks];
                          next[i] = { ...next[i], due_date: e.target.value };
                          setDraft({ ...draft, tasks: next });
                        }}
                      />
                    </div>
                  </div>
                  <p className="evidence muted">
                    Evidence: &quot;{task.evidence_quote}&quot; · confidence {task.confidence}
                  </p>
                </div>
              ))
            )}
          </section>

          <div className="card action-bar">
            <p className="muted">
              Edit any field above, approve or reject each section, then confirm your selection.
            </p>
            <div className="action-row">
              <button type="button" className="secondary" onClick={rejectAll} disabled={loading}>
                Reject all sections
              </button>
              <button type="button" className="secondary" onClick={approveAll} disabled={loading}>
                Approve all sections
              </button>
              <button type="button" onClick={confirmSelection} disabled={loading}>
                Confirm selection
              </button>
            </div>
          </div>
        </>
      )}

      {run.status === "approved" && approved && (
        <div className="card">
          <h3>Confirmed for execute</h3>
          <ul className="confirmed-list">
            <li>Email: {approved.sections?.emails ? "yes" : "no"}</li>
            <li>CRM: {approved.sections?.crm ? "yes" : "no"}</li>
            <li>Tasks: {approved.sections?.tasks ? "yes" : "no"}</li>
          </ul>
          <button type="button" onClick={execute} disabled={loading}>
            Execute approved actions
          </button>
        </div>
      )}

      {run.execution_log && (
        <div className="card">
          <h3>Execution log</h3>
          {run.execution_log.steps?.map((s: any, i: number) => (
            <p key={i}>
              {s.step}: {s.success ? "OK" : "FAIL"} {s.message || s.error}
            </p>
          ))}
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
    </AppShell>
  );
}

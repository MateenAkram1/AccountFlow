"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { API_URL, apiFetch } from "@/lib/api";

type Status = {
  mock_mode: boolean;
  hubspot: { configured: boolean; mode: string };
  gmail: { oauth_app_configured: boolean; connected: boolean; connect_url: string | null };
  jira: { configured: boolean; selected_project: { key: string; name?: string } | null };
};

type Ping = {
  mock_mode: boolean;
  note?: string;
  hubspot?: { ok: boolean; error?: string; first_deal_id?: string };
  gmail?: { ok: boolean; error?: string; email?: string };
  jira?: { ok: boolean; error?: string; user?: string; project_key?: string };
};

type JiraProject = { key: string; name?: string; id?: string };

export default function ConnectPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [ping, setPing] = useState<Ping | null>(null);
  const [projects, setProjects] = useState<JiraProject[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

  const load = async () => {
    try {
      const s = await apiFetch<Status>("/integrations/status");
      setStatus(s);
      if (s.jira.selected_project?.key) {
        setSelectedKey(s.jira.selected_project.key);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load status");
    }
  };

  const loadProjects = async () => {
    setError("");
    try {
      const data = await apiFetch<{ projects: JiraProject[]; selected?: JiraProject | null }>(
        "/integrations/jira/projects"
      );
      setProjects(data.projects || []);
      if (data.selected?.key) {
        setSelectedKey(data.selected.key);
      } else if (data.projects?.length && !selectedKey) {
        setSelectedKey(data.projects[0].key);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Jira projects");
    }
  };

  useEffect(() => {
    load().then(loadProjects);
  }, []);

  const saveProject = async () => {
    if (!selectedKey) {
      setError("Select a Jira project first");
      return;
    }
    setLoading(true);
    setError("");
    setSavedMsg("");
    try {
      const project = projects.find((p) => p.key === selectedKey);
      await apiFetch("/integrations/jira/project", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_key: selectedKey,
          project_name: project?.name || null,
        }),
      });
      setSavedMsg(`Saved project ${selectedKey}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save project");
    } finally {
      setLoading(false);
    }
  };

  const runPing = async () => {
    setLoading(true);
    setError("");
    try {
      const p = await apiFetch<Ping>("/integrations/ping");
      setPing(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ping failed");
    } finally {
      setLoading(false);
    }
  };

  const disconnectGmail = async () => {
    setLoading(true);
    try {
      await apiFetch("/auth/google/gmail/disconnect", { method: "POST" });
      await load();
      setPing(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Disconnect failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <header className="inbox-header">
        <div>
          <h1 className="page-title">Connect integrations</h1>
          <p className="lede">
            HubSpot and Jira use <Link href="/settings/credentials">your credentials</Link>. Gmail needs a
            one-time browser connect. Pick your Jira project here.
          </p>
        </div>
      </header>

      {status?.mock_mode && (
        <div className="warning-box">
          <strong>Mock mode is ON</strong> (<code>INTEGRATIONS_MOCK=true</code>).
          Set it to <code>false</code> in <code>.env</code> and restart the API for live execute.
        </div>
      )}

      <div className="card">
        <h3>HubSpot</h3>
        <p>
          Status:{" "}
          <strong>{status?.hubspot.configured ? "Token configured" : "Missing token"}</strong>
        </p>
        <p className="muted">
          Add your token in <Link href="/settings/credentials">Settings → Credentials</Link>.
        </p>
      </div>

      <div className="card">
        <h3>Gmail</h3>
        <p>
          OAuth app:{" "}
          <strong>{status?.gmail.oauth_app_configured ? "configured" : "missing client id/secret"}</strong>
        </p>
        <p>
          Connected: <strong>{status?.gmail.connected ? "yes" : "no"}</strong>
        </p>
        <div className="action-row">
          {status?.gmail.oauth_app_configured && !status.gmail.connected && (
            <a href={`${API_URL}${status.gmail.connect_url || "/auth/google/gmail/start"}`}>
              <button type="button">Connect Gmail</button>
            </a>
          )}
          {status?.gmail.connected && (
            <button type="button" className="secondary" onClick={disconnectGmail} disabled={loading}>
              Disconnect Gmail
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Jira project</h3>
        <p>
          Credentials:{" "}
          <strong>{status?.jira.configured ? "Configured" : "Missing"}</strong>
        </p>
        <p className="muted">
          Select which project tasks should be created in. Credentials come from Settings.
        </p>
        {projects.length === 0 ? (
          <p className="muted">
            No projects loaded yet. Save Jira credentials in Settings, then refresh.
          </p>
        ) : (
          <select value={selectedKey} onChange={(e) => setSelectedKey(e.target.value)}>
            {projects.map((p) => (
              <option key={p.key} value={p.key}>
                {p.name || p.key} ({p.key})
              </option>
            ))}
          </select>
        )}
        <div className="action-row">
          <button type="button" className="secondary" onClick={loadProjects} disabled={loading}>
            Refresh projects
          </button>
          <button type="button" onClick={saveProject} disabled={loading || !selectedKey}>
            Save project
          </button>
        </div>
        {status?.jira.selected_project?.key && (
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            Active: <strong>{status.jira.selected_project.key}</strong>
            {status.jira.selected_project.name ? ` — ${status.jira.selected_project.name}` : ""}
          </p>
        )}
        {savedMsg && <p style={{ color: "#00ba7c" }}>{savedMsg}</p>}
      </div>

      <div className="card action-bar">
        <button type="button" onClick={runPing} disabled={loading}>
          {loading ? "Checking…" : "Test live connections"}
        </button>
        {ping && (
          <div style={{ marginTop: "1rem" }}>
            {ping.note && <p className="muted">{ping.note}</p>}
            {ping.hubspot && (
              <p>
                HubSpot: {ping.hubspot.ok ? `OK (sample deal ${ping.hubspot.first_deal_id || "—"})` : `FAIL — ${ping.hubspot.error}`}
              </p>
            )}
            {ping.gmail && (
              <p>
                Gmail: {ping.gmail.ok ? `OK (${ping.gmail.email})` : `FAIL — ${ping.gmail.error}`}
              </p>
            )}
            {ping.jira && (
              <p>
                Jira: {ping.jira.ok ? `OK (${ping.jira.user}, project ${ping.jira.project_key || "—"})` : `FAIL — ${ping.jira.error}`}
              </p>
            )}
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}
    </AppShell>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { apiFetch, fetchMe, type Me } from "@/lib/api";

type CredStatus = {
  hubspot: { configured: boolean; hint: string | null };
  jira: {
    configured: boolean;
    hint: string | null;
    site_url?: string;
    email?: string;
  };
  llm: { configured: boolean; hint: string | null; provider?: string; model?: string };
  stt: { configured: boolean; hint: string | null; provider?: string };
};

export default function CredentialsSettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState<CredStatus | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [hubspotToken, setHubspotToken] = useState("");
  const [jiraSite, setJiraSite] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [llmProvider, setLlmProvider] = useState("gemini");
  const [llmKey, setLlmKey] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [llmBase, setLlmBase] = useState("");
  const [sttProvider, setSttProvider] = useState("deepgram");
  const [sttKey, setSttKey] = useState("");

  const load = async () => {
    const user = await fetchMe();
    setMe(user);
    if (!user) {
      window.location.href = "/login";
      return;
    }
    const s = await apiFetch<CredStatus>("/me/credentials/status");
    setStatus(s);
    if (s.jira.site_url) setJiraSite(s.jira.site_url);
    if (s.jira.email) setJiraEmail(s.jira.email);
    if (s.llm.provider) setLlmProvider(s.llm.provider);
    if (s.llm.model) setLlmModel(s.llm.model || "");
    if (s.stt.provider) setSttProvider(s.stt.provider);
  };

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const save = async (provider: string, body: Record<string, unknown>) => {
    setError("");
    setMessage("");
    await apiFetch(`/me/credentials/${provider}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setMessage(`Saved ${provider} credentials`);
    await load();
  };

  const onHubspot = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await save("hubspot", { access_token: hubspotToken });
      setHubspotToken("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const onJira = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await save("jira", {
        site_url: jiraSite,
        email: jiraEmail,
        api_token: jiraToken,
      });
      setJiraToken("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const onLlm = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await save("llm", {
        provider: llmProvider,
        api_key: llmProvider === "mock" ? "" : llmKey,
        model: llmModel || null,
        base_url: llmBase || null,
      });
      setLlmKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const onStt = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await save("stt", {
        provider: sttProvider,
        api_key: sttProvider === "mock" ? "" : sttKey,
      });
      setSttKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const remove = async (provider: string) => {
    setError("");
    try {
      await apiFetch(`/me/credentials/${provider}`, { method: "DELETE" });
      setMessage(`Removed ${provider}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (!me) {
    return (
      <AppShell>
        <p className="muted">Loading…</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="page-title">Your API credentials</h1>
      <p className="lede">
        Keys are Fernet-encrypted on the server and never shown again. Paste a new value to rotate.
        Pick any major LLM — you are not locked to one vendor.
      </p>
      {message && <p style={{ color: "var(--ok)" }}>{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="card">
        <h2>HubSpot {status?.hubspot.configured ? `(${status.hubspot.hint})` : "(not set)"}</h2>
        <form onSubmit={onHubspot}>
          <input
            type="password"
            autoComplete="off"
            placeholder="Private app / access token"
            value={hubspotToken}
            onChange={(e) => setHubspotToken(e.target.value)}
            required
          />
          <div className="action-row">
            <button type="submit">Save HubSpot</button>
            {status?.hubspot.configured && (
              <button type="button" className="secondary" onClick={() => remove("hubspot")}>
                Remove
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Jira {status?.jira.configured ? `(${status.jira.hint})` : "(not set)"}</h2>
        <form onSubmit={onJira}>
          <input
            type="url"
            placeholder="https://your-site.atlassian.net"
            value={jiraSite}
            onChange={(e) => setJiraSite(e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Atlassian account email"
            value={jiraEmail}
            onChange={(e) => setJiraEmail(e.target.value)}
            required
          />
          <input
            type="password"
            autoComplete="off"
            placeholder="API token"
            value={jiraToken}
            onChange={(e) => setJiraToken(e.target.value)}
            required
          />
          <div className="action-row">
            <button type="submit">Save Jira</button>
            {status?.jira.configured && (
              <button type="button" className="secondary" onClick={() => remove("jira")}>
                Remove
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="card">
        <h2>LLM {status?.llm.configured ? `(${status.llm.hint})` : "(not set)"}</h2>
        <form onSubmit={onLlm}>
          <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
            <option value="mock">mock (demo, no key)</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="gemini">Google Gemini</option>
            <option value="groq">Groq</option>
            <option value="ollama_cloud">Ollama Cloud</option>
          </select>
          {llmProvider !== "mock" && (
            <input
              type="password"
              autoComplete="off"
              placeholder="API key"
              value={llmKey}
              onChange={(e) => setLlmKey(e.target.value)}
              required
            />
          )}
          <input
            type="text"
            placeholder="Model (optional — e.g. gpt-4o-mini, claude-sonnet-4-20250514)"
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
          />
          {(llmProvider === "openai" || llmProvider === "ollama_cloud" || llmProvider === "groq") && (
            <input
              type="url"
              placeholder="Base URL (optional)"
              value={llmBase}
              onChange={(e) => setLlmBase(e.target.value)}
            />
          )}
          <div className="action-row">
            <button type="submit">Save LLM</button>
            {status?.llm.configured && (
              <button type="button" className="secondary" onClick={() => remove("llm")}>
                Remove
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Speech-to-text {status?.stt.configured ? `(${status.stt.hint})` : "(not set)"}</h2>
        <form onSubmit={onStt}>
          <select value={sttProvider} onChange={(e) => setSttProvider(e.target.value)}>
            <option value="mock">mock (no key)</option>
            <option value="deepgram">deepgram</option>
          </select>
          {sttProvider !== "mock" && (
            <input
              type="password"
              autoComplete="off"
              placeholder="API key"
              value={sttKey}
              onChange={(e) => setSttKey(e.target.value)}
              required
            />
          )}
          <div className="action-row">
            <button type="submit">Save STT</button>
            {status?.stt.configured && (
              <button type="button" className="secondary" onClick={() => remove("stt")}>
                Remove
              </button>
            )}
          </div>
        </form>
      </section>
    </AppShell>
  );
}

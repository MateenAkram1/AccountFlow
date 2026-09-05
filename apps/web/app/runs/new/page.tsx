"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { apiFetch, createRun } from "@/lib/api";

type Deal = { id: string; name: string; stage?: string; amount?: string };

type SowSummary = {
  id: string;
  name: string;
  preview: string;
  source_filename?: string | null;
  updated_at: string;
};

export default function NewRunPage() {
  const router = useRouter();
  const [transcript, setTranscript] = useState("");
  const [scopeText, setScopeText] = useState("");
  const [sowName, setSowName] = useState("");
  const [saveSow, setSaveSow] = useState(false);
  const [savedSows, setSavedSows] = useState<SowSummary[]>([]);
  const [selectedSowId, setSelectedSowId] = useState("");
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [sowFile, setSowFile] = useState<File | null>(null);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [dealId, setDealId] = useState("");
  const [recording, setRecording] = useState(false);
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [error, setError] = useState("");
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const loadDeals = async () => {
    setLoadingDeals(true);
    setError("");
    try {
      const data = await apiFetch<{ deals: Deal[] }>("/integrations/hubspot/deals");
      setDeals(data.deals || []);
      if (data.deals?.length && !dealId) {
        setDealId(data.deals[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load HubSpot deals");
    } finally {
      setLoadingDeals(false);
    }
  };

  const loadSows = async () => {
    try {
      const list = await apiFetch<SowSummary[]>("/sows");
      setSavedSows(list);
    } catch {
      setSavedSows([]);
    }
  };

  const ensureDeal = async () => {
    setLoadingDeals(true);
    setError("");
    try {
      const deal = await apiFetch<Deal & { created?: boolean }>(
        "/integrations/hubspot/deals/ensure",
        { method: "POST" }
      );
      await loadDeals();
      if (deal.id) setDealId(deal.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create HubSpot deal");
    } finally {
      setLoadingDeals(false);
    }
  };

  useEffect(() => {
    loadDeals();
    loadSows();
  }, []);

  const pickSavedSow = async (id: string) => {
    setSelectedSowId(id);
    setSowFile(null);
    if (!id) return;
    try {
      const sow = await apiFetch<{ name: string; content: string }>(`/sows/${id}`);
      setScopeText(sow.content);
      setSowName(sow.name);
      setSaveSow(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load SOW");
    }
  };

  const startRecording = async () => {
    if (!consent) {
      setError("Please confirm recording consent first.");
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunks.current = [];
    recorder.ondataavailable = (e) => chunks.current.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
    };
    recorder.start();
    mediaRecorder.current = recorder;
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorder.current?.stop();
    setRecording(false);
  };

  const persistSowIfNeeded = async () => {
    if (!saveSow) return;
    const content = scopeText.trim();
    if (!content && !sowFile) return;
    let bodyContent = content;
    if (sowFile && !content) {
      // Upload file directly into library
      const fd = new FormData();
      fd.append("file", sowFile);
      if (sowName.trim()) fd.append("name", sowName.trim());
      await apiFetch("/sows/upload", { method: "POST", body: fd });
      await loadSows();
      return;
    }
    await apiFetch("/sows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: sowName.trim() || sowFile?.name || "Saved SOW",
        content: bodyContent,
      }),
    });
    await loadSows();
  };

  const submit = async (audioBlob?: Blob) => {
    if (!dealId.trim()) {
      setError("Select or enter a HubSpot deal id before processing.");
      return;
    }
    const hasTranscript =
      Boolean(audioBlob) || Boolean(transcriptFile) || Boolean(transcript.trim());
    if (!hasTranscript) {
      setError("Provide a transcript (paste or .txt/.pdf) or a recording.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (saveSow && (scopeText.trim() || sowFile)) {
        await persistSowIfNeeded();
      }

      const form = new FormData();
      if (dealId.startsWith("demo-")) {
        form.append(
          "account_json",
          JSON.stringify({
            deal_id: dealId,
            company: "Acme Corp",
            stage: "discovery",
            amount: 40000,
            contacts: [{ name: "Sarah Chen", role: "CTO", email: "sarah@acme.example" }],
            notes: [],
          })
        );
      } else {
        form.append("deal_id", dealId.trim());
      }

      if (audioBlob) {
        form.append("audio", audioBlob, "recording.webm");
      } else if (transcriptFile) {
        form.append("transcript_file", transcriptFile);
      } else {
        form.append("transcript", transcript);
      }

      if (sowFile) {
        form.append("sow_file", sowFile);
      } else if (selectedSowId) {
        form.append("sow_id", selectedSowId);
      } else if (scopeText.trim()) {
        form.append("scope_text", scopeText.trim());
      }

      const run = await createRun(form);
      router.push(`/runs/${run.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (chunks.current.length > 0 && !recording) {
      const blob = new Blob(chunks.current, { type: "audio/webm" });
      await submit(blob);
    } else {
      await submit();
    }
  };

  return (
    <AppShell>
      <h1 className="page-title">New Run</h1>
      <p className="lede">
        Upload or paste a transcript, attach a deal, and optionally reuse a saved SOW — then approve
        before anything sends.
      </p>

      <div className="card">
        <h3>HubSpot deal</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          CRM execute needs a <strong>real HubSpot deal id</strong> when mock mode is off.
        </p>
        {deals.length > 0 ? (
          <select value={dealId} onChange={(e) => setDealId(e.target.value)}>
            {deals.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id}) {d.stage ? `— ${d.stage}` : ""}
              </option>
            ))}
          </select>
        ) : (
          <p className="muted">
            {loadingDeals ? "Loading deals…" : "No deals found yet — refresh or create a sample."}
          </p>
        )}
        <label>Or paste deal id</label>
        <input
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          placeholder="HubSpot deal id"
        />
        <div className="action-row">
          <button type="button" className="secondary" onClick={loadDeals} disabled={loadingDeals}>
            Refresh deals
          </button>
          <button type="button" className="secondary" onClick={ensureDeal} disabled={loadingDeals}>
            Create sample deal
          </button>
        </div>
      </div>

      <div className="card">
        <label className="checkbox-row">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          I confirm participants know this call may be recorded or processed.
        </label>
      </div>

      <div className="card">
        <h3>Transcript</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Paste text, upload <strong>.txt / .pdf</strong>, or record audio.
        </p>
        <label>Upload transcript file</label>
        <input
          type="file"
          accept=".txt,.text,.md,.pdf,text/plain,application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            setTranscriptFile(f);
            if (f) chunks.current = [];
          }}
        />
        {transcriptFile && (
          <p className="muted">
            Selected: {transcriptFile.name}{" "}
            <button
              type="button"
              className="secondary"
              style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
              onClick={() => setTranscriptFile(null)}
            >
              Clear file
            </button>
          </p>
        )}
        <h4 style={{ marginBottom: "0.5rem" }}>Record audio</h4>
        {!recording ? (
          <button type="button" onClick={startRecording} disabled={!consent || Boolean(transcriptFile)}>
            Start recording
          </button>
        ) : (
          <button type="button" onClick={stopRecording}>
            Stop recording
          </button>
        )}
        <h4 style={{ marginTop: "1rem", marginBottom: "0.5rem" }}>Or paste transcript</h4>
        <textarea
          rows={8}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Paste meeting transcript..."
          disabled={Boolean(transcriptFile)}
        />
      </div>

      <div className="card">
        <h3>SOW / scope (optional)</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Reuse a saved SOW, upload <strong>.txt / .pdf</strong>, or paste. Scope Verifier skips if
          empty.
        </p>

        <label>Saved SOWs</label>
        <select
          value={selectedSowId}
          onChange={(e) => pickSavedSow(e.target.value)}
          disabled={Boolean(sowFile)}
        >
          <option value="">— None / paste or upload —</option>
          {savedSows.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {savedSows.length === 0 && (
          <p className="muted">No saved SOWs yet. Upload or paste one and check “Save for reuse”.</p>
        )}

        <label>Upload SOW file</label>
        <input
          type="file"
          accept=".txt,.text,.md,.pdf,text/plain,application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            setSowFile(f);
            if (f) {
              setSelectedSowId("");
              if (!sowName) setSowName(f.name.replace(/\.(pdf|txt|md)$/i, ""));
            }
          }}
        />
        {sowFile && (
          <p className="muted">
            Selected: {sowFile.name}{" "}
            <button
              type="button"
              className="secondary"
              style={{ padding: "0.25rem 0.6rem", fontSize: "0.8rem" }}
              onClick={() => setSowFile(null)}
            >
              Clear file
            </button>
          </p>
        )}

        <label>Or paste SOW text</label>
        <textarea
          rows={5}
          value={scopeText}
          onChange={(e) => {
            setScopeText(e.target.value);
            if (e.target.value) setSelectedSowId("");
          }}
          placeholder="Paste SOW text for scope verification..."
          disabled={Boolean(sowFile)}
        />

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={saveSow}
            onChange={(e) => setSaveSow(e.target.checked)}
            disabled={Boolean(selectedSowId) && !sowFile && !scopeText}
          />
          Save this SOW to my library for future meetings
        </label>
        {saveSow && (
          <>
            <label>SOW name</label>
            <input
              value={sowName}
              onChange={(e) => setSowName(e.target.value)}
              placeholder="e.g. Acme Corp SOW 2026"
            />
          </>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      <button type="button" onClick={handleSubmit} disabled={loading || !dealId}>
        {loading ? "Processing…" : "Process meeting"}
      </button>
    </AppShell>
  );
}

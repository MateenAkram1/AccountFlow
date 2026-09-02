"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createRun } from "@/lib/api";

const SAMPLE_ACCOUNT = JSON.stringify({
  deal_id: "demo-001",
  company: "Acme Corp",
  stage: "discovery",
  amount: 40000,
  close_date: "2026-03-31",
  contacts: [{ name: "Sarah Chen", role: "CTO", email: "sarah@acme.example" }],
  notes: ["Feb 10: Discussed API integration timeline"],
});

export default function NewRunPage() {
  const router = useRouter();
  const [transcript, setTranscript] = useState("");
  const [scopeText, setScopeText] = useState("");
  const [recording, setRecording] = useState(false);
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

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

  const submit = async (audioBlob?: Blob) => {
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("account_json", SAMPLE_ACCOUNT);
      if (audioBlob) {
        form.append("audio", audioBlob, "recording.webm");
      } else {
        form.append("transcript", transcript);
      }
      if (scopeText) form.append("scope_text", scopeText);
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
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <h1>New Run</h1>
      <div className="card">
        <label>
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          {" "}I confirm all participants are aware this call is being recorded/processed.
        </label>
      </div>
      <div className="card">
        <h3>Record audio</h3>
        {!recording ? (
          <button onClick={startRecording} disabled={!consent}>Start recording</button>
        ) : (
          <button onClick={stopRecording}>Stop recording</button>
        )}
      </div>
      <div className="card">
        <h3>Or paste transcript</h3>
        <textarea rows={8} value={transcript} onChange={(e) => setTranscript(e.target.value)} placeholder="Paste meeting transcript..." />
      </div>
      <div className="card">
        <h3>SOW / scope (optional)</h3>
        <textarea rows={4} value={scopeText} onChange={(e) => setScopeText(e.target.value)} placeholder="Paste SOW text for scope verification..." />
      </div>
      {error && <p style={{ color: "#f4212e" }}>{error}</p>}
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Processing..." : "Process meeting"}
      </button>
    </main>
  );
}

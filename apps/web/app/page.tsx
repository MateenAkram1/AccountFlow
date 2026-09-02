"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
      <h1>AccountFlow OS</h1>
      <p>Meeting + account context → scope verify → approve → execute</p>
      <div className="card">
        <h2>Start a run</h2>
        <p>Upload a transcript or record audio, review drafts, then execute to Gmail, HubSpot, and Jira.</p>
        <Link href="/runs/new">
          <button>New Run</button>
        </Link>
      </div>
      <div className="card">
        <h2>Recent runs</h2>
        <Link href="/runs">
          <button className="secondary">View runs</button>
        </Link>
      </div>
    </main>
  );
}

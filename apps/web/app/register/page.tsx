"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { FlowCanvas } from "@/components/FlowCanvas";
import { apiFetch } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name: name || null }),
      });
      setPassword("");
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-stage">
      <div className="auth-layout">
        <div className="auth-visual">
          <FlowCanvas />
        </div>
        <div className="auth-card" style={{ margin: 0 }}>
          <Link href="/" className="brand-mark" style={{ marginBottom: "1rem", display: "inline-flex" }}>
            <span className="brand-mark__glyph" aria-hidden />
            AccountFlow OS
          </Link>
          <h1 style={{ marginTop: 0 }}>Claim your canvas</h1>
          <p className="lede">Encrypted keys. Human approvals. Your loop.</p>
          {error && <p className="error">{error}</p>}
          <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.35rem" }}>
            <label>
              Name
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              Email
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password (min 8)
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Creating…" : "Register"}
            </button>
          </form>
          <p className="muted" style={{ marginTop: "1.25rem" }}>
            Already have an account? <Link href="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

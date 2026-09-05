"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FlowCanvas } from "@/components/FlowCanvas";
import { API_URL, apiFetch } from "@/lib/api";

export default function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const googleError = params.get("google");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiFetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      setPassword("");
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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
          <h1 style={{ marginTop: 0 }}>Enter the loop</h1>
          <p className="lede">Sign in to approve actions on your canvas.</p>
          {googleError === "error" && <p className="error">Google sign-in failed. Try again.</p>}
          {error && <p className="error">{error}</p>}
          <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.35rem" }}>
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
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p style={{ marginTop: "1.25rem" }}>
            <a href={`${API_URL}/auth/google/login/start`}>Continue with Google</a>
          </p>
          <p className="muted">
            New here? <Link href="/register">Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

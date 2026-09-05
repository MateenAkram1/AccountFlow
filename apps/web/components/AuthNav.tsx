"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchMe, logout, type Me } from "@/lib/api";

export function AuthNav() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);

  useEffect(() => {
    fetchMe().then(setMe);
  }, []);

  if (me === undefined) {
    return null;
  }

  if (!me) {
    return (
      <nav style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <Link href="/login">Sign in</Link>
        <Link href="/register">Register</Link>
      </nav>
    );
  }

  return (
    <nav
      style={{
        display: "flex",
        gap: "1rem",
        marginBottom: "1.5rem",
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <span style={{ opacity: 0.8 }}>{me.email}</span>
      <Link href="/">Home</Link>
      <Link href="/runs/new">New Run</Link>
      <Link href="/connect">Connect</Link>
      <Link href="/settings/credentials">Credentials</Link>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          await logout();
          window.location.href = "/login";
        }}
      >
        Sign out
      </button>
    </nav>
  );
}

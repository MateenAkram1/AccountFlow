"use client";

import { Suspense } from "react";
import LoginInner from "./LoginInner";

export default function LoginPage() {
  return (
    <Suspense fallback={<main style={{ padding: "2rem" }}>Loading…</main>}>
      <LoginInner />
    </Suspense>
  );
}

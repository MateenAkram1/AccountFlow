"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { fetchMe, logout, type Me } from "@/lib/api";

export function AppShell({
  children,
  bare = false,
  reveal = false,
}: {
  children: React.ReactNode;
  bare?: boolean;
  reveal?: boolean;
}) {
  const [me, setMe] = useState<Me | null | undefined>(undefined);

  useEffect(() => {
    fetchMe().then(setMe);
  }, []);

  return (
    <div className="shell">
      {!bare && (
        <motion.header
          className="topbar"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: reveal ? 0.7 : 0 }}
        >
          <Link href={me ? "/" : "/login"} className="brand-mark">
            <span className="brand-mark__glyph" aria-hidden />
            AccountFlow OS
          </Link>
          <nav className="nav-links" aria-label="Primary">
            {me === undefined ? null : me ? (
              <>
                <span className="nav-email">{me.email}</span>
                <Link href="/runs/new">New Run</Link>
                <Link href="/runs">Runs</Link>
                <Link href="/connect">Connect</Link>
                <Link href="/settings/credentials">Credentials</Link>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={async () => {
                    await logout();
                    window.location.href = "/login";
                  }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link href="/login">Sign in</Link>
                <Link href="/register">Register</Link>
              </>
            )}
          </nav>
        </motion.header>
      )}
      {children}
    </div>
  );
}

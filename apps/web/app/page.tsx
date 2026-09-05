"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { CapabilityRail } from "@/components/CapabilityRail";
import { FlowCanvas } from "@/components/FlowCanvas";
import { PageReveal } from "@/components/PageReveal";
import { fetchMe, type Me } from "@/lib/api";

export default function HomePage() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    fetchMe().then((u) => {
      setMe(u);
      if (!u) window.location.href = "/login";
    });
  }, []);

  if (!me) {
    return (
      <AppShell bare>
        <p className="muted">Checking session…</p>
      </AppShell>
    );
  }

  return (
    <PageReveal>
      <AppShell reveal>
        <section className="hero-compose" aria-label="AccountFlow OS">
          <div className="hero-copy">
            <h1 className="hero-brand">AccountFlow OS</h1>
            <p className="hero-line">Meeting in. Actions out — with a human in the loop.</p>
            <p className="hero-sub">
              Scope-check every ask, approve every outbound touch, then execute to Gmail, HubSpot, and
              Jira with your own keys.
            </p>
            <div className="cta-row">
              <Link href="/runs/new">
                <button type="button">Start a run</button>
              </Link>
              <Link href="/settings/credentials">
                <button type="button" className="secondary">
                  Wire your stack
                </button>
              </Link>
            </div>
          </div>
          <FlowCanvas />
        </section>

        <section className="story" aria-label="How it works">
          <div>
            <h2>The product is the graph</h2>
            <p>
              Like a canvas for operators: each node is a step you can inspect. Signal only moves
              forward when you approve — the same discipline that makes award-winning product sites
              feel intentional, applied to your post-call grind.
            </p>
          </div>
          <ol className="story-steps">
            {[
              ["01 Capture", "Paste a transcript or record with consent."],
              ["02 Verify", "Scope Verifier cites the SOW or skips cleanly."],
              ["03 Approve", "Edit drafts section-by-section in the inbox."],
              ["04 Execute", "Ship to the tools you already live in."],
            ].map(([title, body], i) => (
              <motion.li
                key={title}
                initial={{ opacity: 0, x: 16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ delay: i * 0.05, duration: 0.45 }}
              >
                <strong>{title}</strong>
                <span>{body}</span>
              </motion.li>
            ))}
          </ol>
        </section>

        <CapabilityRail />

        <div className="home-footer-cta">
          <div>
            <h2>Ready when the call ends</h2>
            <p>Open a run, review once, close the loop.</p>
          </div>
          <Link href="/runs/new">
            <button type="button">New Run</button>
          </Link>
        </div>
      </AppShell>
    </PageReveal>
  );
}

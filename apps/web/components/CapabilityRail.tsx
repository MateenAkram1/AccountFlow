"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useRef } from "react";

const ITEMS = [
  {
    title: "Scope Verifier",
    body: "Flags out-of-scope asks against the SOW before anyone drafts a reply.",
  },
  {
    title: "Approval Inbox",
    body: "Edit emails, CRM fields, and tasks. Approve by section — nothing auto-sends.",
  },
  {
    title: "Bring your keys",
    body: "Encrypted vault for HubSpot, Jira, Gmail OAuth, and the LLM you actually use.",
  },
  {
    title: "Execute once",
    body: "Confirmed packages land in Gmail, HubSpot, and Jira with an audit trail.",
  },
];

export function CapabilityRail() {
  const reduce = useReducedMotion();
  const scroller = useRef<HTMLDivElement>(null);

  const nudge = (dir: number) => {
    scroller.current?.scrollBy({ left: dir * 320, behavior: "smooth" });
  };

  return (
    <section className="rail-section" aria-label="Capabilities">
      <div className="rail-head">
        <h2>Built like a graph, used like a cockpit</h2>
        <div className="rail-controls">
          <button type="button" className="ghost-btn" onClick={() => nudge(-1)} aria-label="Previous">
            ←
          </button>
          <button type="button" className="ghost-btn" onClick={() => nudge(1)} aria-label="Next">
            →
          </button>
        </div>
      </div>
      <div className="rail" ref={scroller}>
        {ITEMS.map((item, i) => (
          <motion.article
            key={item.title}
            className="rail-card"
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ delay: i * 0.06, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="rail-index">0{i + 1}</span>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

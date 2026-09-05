"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

const NODES = [
  { id: "meet", label: "Meeting", x: 8, y: 42 },
  { id: "scope", label: "Scope", x: 34, y: 28 },
  { id: "approve", label: "Approve", x: 60, y: 48 },
  { id: "execute", label: "Execute", x: 86, y: 34 },
] as const;

export function FlowCanvas({ className = "" }: { className?: string }) {
  const reduce = useReducedMotion();
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(() => {
      setActive((i) => (i + 1) % NODES.length);
    }, 1800);
    return () => window.clearInterval(id);
  }, [reduce]);

  return (
    <div className={`flow-canvas ${className}`} aria-hidden>
      <div className="flow-canvas__grid" />
      <svg className="flow-canvas__wires" viewBox="0 0 100 100" preserveAspectRatio="none">
        {NODES.slice(0, -1).map((n, i) => {
          const next = NODES[i + 1];
          const midX = (n.x + next.x) / 2;
          const lit = active > i;
          return (
            <path
              key={n.id}
              d={`M ${n.x} ${n.y} C ${midX} ${n.y}, ${midX} ${next.y}, ${next.x} ${next.y}`}
              className={lit ? "wire wire--lit" : "wire"}
            />
          );
        })}
        {!reduce && (
          <motion.circle
            r="1.1"
            fill="var(--signal)"
            initial={false}
            animate={{
              cx: NODES[active].x,
              cy: NODES[active].y,
            }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          />
        )}
      </svg>
      {NODES.map((n, i) => (
        <button
          key={n.id}
          type="button"
          className={`flow-node ${active === i ? "flow-node--active" : ""}`}
          style={{ left: `${n.x}%`, top: `${n.y}%` }}
          onClick={() => setActive(i)}
          tabIndex={-1}
        >
          <span className="flow-node__dot" />
          <span className="flow-node__label">{n.label}</span>
        </button>
      ))}
      <div className="flow-canvas__caption">
        Ideas move as a graph — nothing ships without a human node.
      </div>
    </div>
  );
}

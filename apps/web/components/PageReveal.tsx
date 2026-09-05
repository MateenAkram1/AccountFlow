"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

export function PageReveal({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const [show, setShow] = useState(!reduce);

  useEffect(() => {
    if (reduce) return;
    const t = window.setTimeout(() => setShow(false), 1100);
    return () => window.clearTimeout(t);
  }, [reduce]);

  return (
    <>
      <AnimatePresence>
        {show && (
          <motion.div
            className="page-reveal"
            initial={{ y: 0 }}
            exit={{ y: "-105%" }}
            transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
            aria-hidden
          >
            <motion.p
              className="page-reveal__mark"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4 }}
            >
              AccountFlow OS
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: reduce ? 0 : 0.55, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </>
  );
}

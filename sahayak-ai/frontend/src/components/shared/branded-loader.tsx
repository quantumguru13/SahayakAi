"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

/** Full-screen branded loading state used for auth resolution and route waits. */
export function BrandedLoader({ label }: { label?: string }) {
  return (
    <div className="grid-bg flex h-screen flex-col items-center justify-center gap-5 bg-background">
      <div className="relative">
        <motion.div
          className="absolute inset-0 rounded-2xl bg-primary/40 blur-xl"
          animate={{ opacity: [0.3, 0.7, 0.3], scale: [0.9, 1.1, 0.9] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground"
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        >
          <Sparkles className="h-7 w-7" />
        </motion.div>
      </div>
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-primary"
            animate={{ opacity: [0.2, 1, 0.2] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  );
}

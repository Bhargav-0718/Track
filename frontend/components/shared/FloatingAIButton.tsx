"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, X, MessageSquare, Camera, BarChart2, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils/format";

const ACTIONS = [
  {
    icon: Zap,
    label: "Quick Log",
    description: "Log food instantly",
    color: "bg-emerald-500",
    href: "/log",
  },
  {
    icon: BarChart2,
    label: "Today's Report",
    description: "View AI daily summary",
    color: "bg-indigo-500",
    href: "/insights",
  },
  {
    icon: Camera,
    label: "Compare Progress",
    description: "AI physique analysis",
    color: "bg-blue-500",
    href: "/progress",
  },
  {
    icon: MessageSquare,
    label: "Ask AI",
    description: "Get recommendations",
    color: "bg-violet-500",
    href: "/insights",
  },
] as const;

export function FloatingAIButton() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  return (
    <>
      {/* Backdrop */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Actions menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed bottom-28 right-4 z-50 w-64"
          >
            <div className="glass rounded-2xl p-2 shadow-float space-y-1">
              {ACTIONS.map(({ icon: Icon, label, description, color, href }, i) => (
                <motion.button
                  key={label}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => {
                    setOpen(false);
                    router.push(href);
                  }}
                  className="w-full flex items-center gap-3 p-3 rounded-xl
                             hover:bg-surface-elevated transition-colors text-left"
                >
                  <div
                    className={cn(
                      "w-9 h-9 rounded-xl flex items-center justify-center shrink-0",
                      color
                    )}
                  >
                    <Icon className="w-4.5 h-4.5 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{label}</p>
                    <p className="text-xs text-text-muted">{description}</p>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB */}
      <motion.button
        onClick={() => setOpen(!open)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={cn(
          "fixed bottom-24 right-4 z-50",
          "w-14 h-14 rounded-2xl",
          "flex items-center justify-center",
          "shadow-float transition-all duration-300",
          open
            ? "bg-surface-elevated border border-border"
            : "bg-indigo-gradient shadow-glow-indigo"
        )}
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.div
              key="close"
              initial={{ opacity: 0, rotate: -90 }}
              animate={{ opacity: 1, rotate: 0 }}
              exit={{ opacity: 0, rotate: 90 }}
              transition={{ duration: 0.15 }}
            >
              <X className="w-5 h-5 text-text-primary" />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ opacity: 0, rotate: 90 }}
              animate={{ opacity: 1, rotate: 0 }}
              exit={{ opacity: 0, rotate: -90 }}
              transition={{ duration: 0.15 }}
            >
              <Sparkles className="w-5 h-5 text-white" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </>
  );
}

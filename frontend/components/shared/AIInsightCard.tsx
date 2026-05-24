"use client";

import { motion } from "framer-motion";
import { Sparkles, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils/format";

interface AIInsightCardProps {
  insights: string[];
  motivation?: string;
  loading?: boolean;
  onExpand?: () => void;
  className?: string;
}

export function AIInsightCard({
  insights,
  motivation,
  loading = false,
  onExpand,
  className,
}: AIInsightCardProps) {
  if (loading) {
    return (
      <div className={cn("card-surface p-4 space-y-3", className)}>
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-indigo-500/20 shimmer" />
          <div className="h-4 w-24 rounded bg-surface-elevated shimmer" />
        </div>
        <div className="space-y-2">
          <div className="h-3.5 w-full rounded bg-surface-elevated shimmer" />
          <div className="h-3.5 w-4/5 rounded bg-surface-elevated shimmer" />
        </div>
      </div>
    );
  }

  if (!insights?.length && !motivation) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className={cn(
        "relative overflow-hidden rounded-2xl border border-indigo-500/20 bg-surface",
        "cursor-pointer group",
        className
      )}
      onClick={onExpand}
    >
      {/* Gradient left accent */}
      <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-indigo-gradient" />

      {/* Background glow */}
      <div className="absolute inset-0 bg-indigo-gradient opacity-[0.03] pointer-events-none" />

      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-indigo-500/15 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <span className="text-xs font-semibold text-indigo-400 tracking-wide uppercase">
              AI Insight
            </span>
          </div>
          {onExpand && (
            <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-text-secondary transition-colors" />
          )}
        </div>

        {/* Insights list */}
        <div className="space-y-2">
          {insights.slice(0, 2).map((insight, i) => (
            <p key={i} className="text-sm text-text-secondary leading-relaxed">
              {i === 0 ? (
                <span className="text-text-primary font-medium">{insight}</span>
              ) : (
                insight
              )}
            </p>
          ))}
        </div>

        {/* Motivation */}
        {motivation && (
          <div className="mt-3 pt-3 border-t border-border-subtle">
            <p className="text-sm text-indigo-300 font-medium leading-relaxed">
              {motivation}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

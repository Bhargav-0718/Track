"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils/format";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  icon?: LucideIcon;
  accent?: "emerald" | "blue" | "indigo" | "amber" | "zinc";
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  loading?: boolean;
  className?: string;
  onClick?: () => void;
}

const ACCENT_STYLES = {
  emerald: {
    icon: "bg-emerald-500/15 text-emerald-400",
    value: "text-emerald-400",
    border: "border-emerald-500/20",
  },
  blue: {
    icon: "bg-blue-500/15 text-blue-400",
    value: "text-blue-400",
    border: "border-blue-500/20",
  },
  indigo: {
    icon: "bg-indigo-500/15 text-indigo-400",
    value: "text-indigo-400",
    border: "border-indigo-500/20",
  },
  amber: {
    icon: "bg-amber-500/15 text-amber-400",
    value: "text-amber-400",
    border: "border-amber-500/20",
  },
  zinc: {
    icon: "bg-zinc-700/50 text-zinc-400",
    value: "text-text-primary",
    border: "border-border",
  },
};

export function MetricCard({
  label,
  value,
  unit,
  subtitle,
  icon: Icon,
  accent = "zinc",
  loading = false,
  className,
  onClick,
}: MetricCardProps) {
  const styles = ACCENT_STYLES[accent];

  if (loading) {
    return (
      <div className={cn("card-surface p-4 space-y-3", className)}>
        <div className="flex items-center justify-between">
          <div className="h-3.5 w-20 rounded bg-surface-elevated shimmer" />
          <div className="w-8 h-8 rounded-xl bg-surface-elevated shimmer" />
        </div>
        <div className="h-7 w-24 rounded bg-surface-elevated shimmer" />
        {subtitle && <div className="h-3 w-16 rounded bg-surface-elevated shimmer" />}
      </div>
    );
  }

  return (
    <motion.div
      whileHover={onClick ? { scale: 1.01 } : undefined}
      whileTap={onClick ? { scale: 0.99 } : undefined}
      className={cn(
        "card-surface p-4",
        onClick && "cursor-pointer hover:border-border transition-colors",
        className
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wide">
          {label}
        </span>
        {Icon && (
          <div className={cn("w-8 h-8 rounded-xl flex items-center justify-center", styles.icon)}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-1">
        <span className={cn("text-2xl font-bold tabular-nums", styles.value)}>
          {value}
        </span>
        {unit && (
          <span className="text-sm text-text-muted font-medium">{unit}</span>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-text-muted mt-1">{subtitle}</p>
      )}
    </motion.div>
  );
}

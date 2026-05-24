"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Flame, Zap, Footprints, Dumbbell, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { format } from "date-fns";

import { ProgressRing } from "@/components/shared/ProgressRing";
import { AIInsightCard } from "@/components/shared/AIInsightCard";
import { MetricCard } from "@/components/shared/MetricCard";
import { foodApi } from "@/lib/api/food";
import { analyticsApi } from "@/lib/api/analytics";
import { reportsApi } from "@/lib/api/reports";
import { useAuthStore } from "@/lib/store/auth";
import {
  formatCalories,
  formatGrams,
  getGreeting,
  todayISO,
  cn,
} from "@/lib/utils/format";

// ── Macro bar ─────────────────────────────────────────────────────────────────

function MacroBar({
  label,
  current,
  target,
  color,
}: {
  label: string;
  current: number;
  target: number | null;
  color: string;
}) {
  const pct = target ? Math.min((current / target) * 100, 100) : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-muted font-medium">{label}</span>
        <span className="text-text-secondary tabular-nums">
          {formatGrams(current)}
          {target ? <span className="text-text-muted"> / {formatGrams(target)}</span> : ""}
        </span>
      </div>
      <div className="h-1.5 bg-surface-elevated rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: [0.4, 0, 0.2, 1], delay: 0.2 }}
        />
      </div>
    </div>
  );
}

// ── Streak card ───────────────────────────────────────────────────────────────

function StreakCard({ days, isActive }: { days: number; isActive: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl px-4 py-3"
    >
      <motion.div
        animate={{ scale: [1, 1.1, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="text-2xl"
      >
        🔥
      </motion.div>
      <div>
        <p className="text-sm font-bold text-amber-400">
          {days} day streak
        </p>
        <p className="text-xs text-text-muted">
          {isActive ? "Logged today ✓" : "Log something to keep it going"}
        </p>
      </div>
    </motion.div>
  );
}

// ── Quick add ─────────────────────────────────────────────────────────────────

function QuickAdd() {
  const router = useRouter();
  return (
    <div className="grid grid-cols-2 gap-3">
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => router.push("/log")}
        className="flex items-center gap-2.5 bg-emerald-500/10 border border-emerald-500/20
                   rounded-2xl p-4 hover:bg-emerald-500/15 transition-colors"
      >
        <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center">
          <Flame className="w-4.5 h-4.5 text-white" />
        </div>
        <div className="text-left">
          <p className="text-sm font-semibold text-text-primary">Log Food</p>
          <p className="text-xs text-text-muted">Add a meal</p>
        </div>
      </motion.button>

      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => router.push("/log?tab=workout")}
        className="flex items-center gap-2.5 bg-blue-500/10 border border-blue-500/20
                   rounded-2xl p-4 hover:bg-blue-500/15 transition-colors"
      >
        <div className="w-9 h-9 rounded-xl bg-blue-500 flex items-center justify-center">
          <Dumbbell className="w-4.5 h-4.5 text-white" />
        </div>
        <div className="text-left">
          <p className="text-sm font-semibold text-text-primary">Log Workout</p>
          <p className="text-xs text-text-muted">Track activity</p>
        </div>
      </motion.button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const greeting = getGreeting(user?.display_name?.split(" ")[0]);

  const { data: daily, isLoading: dailyLoading } = useSWR(
    ["daily", todayISO()],
    () => foodApi.getDaily(todayISO())
  );

  const { data: streak } = useSWR(
    "streak",
    () => analyticsApi.getStreak()
  );

  const { data: report, isLoading: reportLoading } = useSWR(
    "today-report",
    () => reportsApi.generate({ report_date: todayISO() }).catch(() => null)
  );

  const targetCal = user?.target_calories ?? 2000;
  const actualCal = daily?.total_calories ?? 0;
  const calPct = Math.min((actualCal / targetCal) * 100, 100);

  const stagger = {
    visible: { transition: { staggerChildren: 0.07 } },
  };
  const fadeUp = {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

  return (
    <div className="px-4 pt-12 pb-4 space-y-5 max-w-md mx-auto">
      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-0.5"
      >
        <p className="text-text-muted text-sm">
          {format(new Date(), "EEEE, MMMM d")}
        </p>
        <h1 className="text-2xl font-bold">
          {greeting.text}{" "}
          <span>{greeting.emoji}</span>
        </h1>
      </motion.div>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
        className="space-y-4"
      >
        {/* Streak */}
        {streak && (
          <motion.div variants={fadeUp}>
            <StreakCard
              days={streak.current_streak_days}
              isActive={streak.is_active_today}
            />
          </motion.div>
        )}

        {/* Calorie ring + summary */}
        <motion.div
          variants={fadeUp}
          className="card-surface p-5"
        >
          <div className="flex items-center gap-5">
            {/* Ring */}
            <ProgressRing value={calPct} size={110} strokeWidth={9} color="#10b981">
              <div className="text-center">
                {dailyLoading ? (
                  <div className="h-7 w-16 rounded bg-surface-elevated shimmer" />
                ) : (
                  <>
                    <p className="text-xl font-bold tabular-nums text-text-primary">
                      {formatCalories(actualCal)}
                    </p>
                    <p className="text-[10px] text-text-muted">kcal</p>
                  </>
                )}
              </div>
            </ProgressRing>

            {/* Macro bars */}
            <div className="flex-1 space-y-3">
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-text-muted font-medium">Calories</span>
                  <span className="text-text-secondary">
                    {formatCalories(actualCal)}
                    <span className="text-text-muted"> / {formatCalories(targetCal)}</span>
                  </span>
                </div>
              </div>
              <MacroBar
                label="Protein"
                current={daily?.total_protein_g ?? 0}
                target={user?.target_protein_g ?? null}
                color="#3b82f6"
              />
              <MacroBar
                label="Carbs"
                current={daily?.total_carbs_g ?? 0}
                target={user?.target_carbs_g ?? null}
                color="#f59e0b"
              />
              <MacroBar
                label="Fat"
                current={daily?.total_fat_g ?? 0}
                target={user?.target_fat_g ?? null}
                color="#8b5cf6"
              />
            </div>
          </div>
        </motion.div>

        {/* Stats row */}
        <motion.div variants={fadeUp} className="grid grid-cols-3 gap-3">
          <div className="card-surface p-3 text-center">
            <p className="text-lg font-bold tabular-nums text-text-primary">
              {daily?.food_count ?? 0}
            </p>
            <p className="text-[10px] text-text-muted mt-0.5">Meals</p>
          </div>
          <div className="card-surface p-3 text-center">
            <p className="text-lg font-bold tabular-nums text-blue-400">
              {formatGrams(daily?.total_protein_g ?? 0)}
            </p>
            <p className="text-[10px] text-text-muted mt-0.5">Protein</p>
          </div>
          <div className="card-surface p-3 text-center">
            <p className="text-lg font-bold tabular-nums text-emerald-400">
              {Math.round(calPct)}%
            </p>
            <p className="text-[10px] text-text-muted mt-0.5">Goal</p>
          </div>
        </motion.div>

        {/* AI Insight */}
        <motion.div variants={fadeUp}>
          {reportLoading ? (
            <AIInsightCard insights={[]} loading={true} />
          ) : report?.behavioral_observations?.length || report?.insights_text ? (
            <AIInsightCard
              insights={
                report.behavioral_observations?.length
                  ? report.behavioral_observations
                  : report.insights_text
                  ? [report.insights_text.slice(0, 200)]
                  : []
              }
              motivation={report.motivation_message ?? undefined}
              onExpand={() => router.push("/insights")}
            />
          ) : null}
        </motion.div>

        {/* Quick add */}
        <motion.div variants={fadeUp}>
          <QuickAdd />
        </motion.div>

        {/* Today's logs preview */}
        {daily && daily.logs.length > 0 && (
          <motion.div variants={fadeUp}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-text-secondary">Today's Meals</h2>
              <button
                onClick={() => router.push("/log")}
                className="flex items-center gap-1 text-xs text-emerald-400"
              >
                View all <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="space-y-2">
              {daily.logs.slice(0, 3).map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between card-surface px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">{log.food_name}</p>
                    <p className="text-xs text-text-muted">
                      {log.portion_description ?? log.meal_type}
                    </p>
                  </div>
                  <span className="text-sm font-bold tabular-nums text-text-primary">
                    {formatCalories(log.calories)}
                    <span className="text-xs text-text-muted font-normal"> kcal</span>
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp, TrendingDown, Minus, Zap, Brain, BarChart3,
  Flame, ChevronDown, ChevronUp, Sparkles, RefreshCw, Star
} from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { format, parseISO } from "date-fns";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, BarChart, Bar
} from "recharts";

import { analyticsApi } from "@/lib/api/analytics";
import { reportsApi } from "@/lib/api/reports";
import { AIInsightCard } from "@/components/shared/AIInsightCard";
import { formatPct, formatScore, todayISO, cn } from "@/lib/utils/format";
import type { DailyReport, ReportStyle } from "@/lib/types";

// ── Consistency ring ──────────────────────────────────────────────────────────

function ConsistencyRing({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "#10b981" : pct >= 60 ? "#3b82f6" : pct >= 40 ? "#f59e0b" : "#71717a";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-16 h-16">
        <svg width={64} height={64} className="-rotate-90">
          <circle cx={32} cy={32} r={26} fill="none" stroke="#27272a" strokeWidth={6} />
          <motion.circle
            cx={32} cy={32} r={26}
            fill="none"
            stroke={color}
            strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={163.4}
            initial={{ strokeDashoffset: 163.4 }}
            animate={{ strokeDashoffset: 163.4 - (pct / 100) * 163.4 }}
            transition={{ duration: 1, ease: [0.4, 0, 0.2, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color }}>{pct}</span>
        </div>
      </div>
      <span className="text-[10px] text-text-muted text-center">{label}</span>
    </div>
  );
}

// ── Trend chart ───────────────────────────────────────────────────────────────

function TrendChart({ period = 30 }: { period?: number }) {
  const { data } = useSWR(
    ["trend", period],
    () => analyticsApi.getTrend(period as 7 | 14 | 30 | 90)
  );

  if (!data) return (
    <div className="h-32 rounded-2xl bg-surface-elevated shimmer" />
  );

  const chartData = data.data_points.map((p) => ({
    date: format(parseISO(p.date), "MMM d"),
    calories: Math.round(p.calories),
    logged: p.logged,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="glass rounded-xl px-3 py-2 text-xs">
        <p className="text-text-primary font-bold">{payload[0].value} kcal</p>
        <p className="text-text-muted">{payload[0].payload.date}</p>
        {!payload[0].payload.logged && (
          <p className="text-zinc-500">No logs</p>
        )}
      </div>
    );
  };

  return (
    <div className="card-surface p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-secondary">Calorie Trend</h3>
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
          avg {Math.round(data.average_calories)} kcal/day
        </div>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <AreaChart data={chartData} margin={{ top: 0, right: 0, left: -32, bottom: 0 }}>
          <defs>
            <linearGradient id="calGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: "#52525b" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={["dataMin - 200", "dataMax + 200"]}
            tick={{ fontSize: 9, fill: "#52525b" }}
            axisLine={false}
            tickLine={false}
          />
          {data.calorie_target && (
            <ReferenceLine
              y={data.calorie_target}
              stroke="#3f3f46"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="calories"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#calGradient)"
            dot={false}
            activeDot={{ r: 5, fill: "#10b981", strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Meal pattern row ──────────────────────────────────────────────────────────

function MealPatternRow({ meal_type, log_frequency_pct, avg_calories, most_common_foods }: {
  meal_type: string;
  log_frequency_pct: number;
  avg_calories: number;
  most_common_foods: string[];
}) {
  const [open, setOpen] = useState(false);
  const pct = log_frequency_pct;
  const color = pct >= 80 ? "#10b981" : pct >= 50 ? "#3b82f6" : "#71717a";

  return (
    <div
      className="cursor-pointer"
      onClick={() => setOpen(!open)}
    >
      <div className="flex items-center gap-3 py-3">
        <div className="w-16 text-xs text-text-muted capitalize">
          {meal_type.replace("_", " ")}
        </div>
        <div className="flex-1 h-2 bg-surface-elevated rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: color }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8 }}
          />
        </div>
        <span className="text-xs font-medium w-10 text-right" style={{ color }}>
          {Math.round(pct)}%
        </span>
        {open ? (
          <ChevronUp className="w-3.5 h-3.5 text-text-muted" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
        )}
      </div>
      <AnimatePresence>
        {open && most_common_foods.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="flex flex-wrap gap-1.5 pb-3 pl-[76px]">
              {most_common_foods.map((food) => (
                <span
                  key={food}
                  className="text-[10px] bg-surface-elevated text-text-muted
                             px-2 py-0.5 rounded-full"
                >
                  {food}
                </span>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Daily report card ─────────────────────────────────────────────────────────

function DailyReportCard({ report }: { report: DailyReport }) {
  const [rated, setRated] = useState(report.user_rating);

  async function handleRate(rating: number) {
    try {
      await reportsApi.rate(report.id, rating);
      setRated(rating);
    } catch {}
  }

  const styles: Record<ReportStyle, { label: string; color: string }> = {
    motivational: { label: "Motivational", color: "text-amber-400" },
    analytical: { label: "Analytical", color: "text-blue-400" },
    brief: { label: "Brief", color: "text-zinc-400" },
    detailed: { label: "Detailed", color: "text-indigo-400" },
  };
  const style = styles[report.report_style as ReportStyle] ?? styles.motivational;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface p-4 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-semibold text-text-secondary">Daily Report</span>
        </div>
        <span className={cn("text-xs", style.color)}>{style.label}</span>
      </div>

      {/* Consistency score */}
      <div className="flex items-center gap-4">
        <div className="text-center">
          <p className="text-3xl font-bold text-text-primary tabular-nums">
            {formatScore(report.consistency_score)}
          </p>
          <p className="text-[10px] text-text-muted">Consistency</p>
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Calories</span>
            <span className="text-text-primary">
              {Math.round(report.calorie_summary.actual)} kcal
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Streak</span>
            <span className="text-amber-400">🔥 {report.streak_days} days</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Net cal</span>
            <span className={report.workout_summary.net_calories < report.calorie_summary.actual
              ? "text-emerald-400" : "text-text-secondary"}>
              {Math.round(report.workout_summary.net_calories)} kcal
            </span>
          </div>
        </div>
      </div>

      {/* Insights */}
      {report.insights_text && (
        <p className="text-sm text-text-secondary leading-relaxed border-t border-border-subtle pt-4">
          {report.insights_text}
        </p>
      )}

      {/* Motivation */}
      {report.motivation_message && (
        <p className="text-sm text-indigo-300 font-medium">
          {report.motivation_message}
        </p>
      )}

      {/* Observations */}
      {report.behavioral_observations?.length > 0 && (
        <div className="space-y-1.5 border-t border-border-subtle pt-3">
          {report.behavioral_observations.map((obs, i) => (
            <div key={i} className="flex gap-2 text-xs text-text-muted">
              <span className="text-emerald-400 shrink-0">•</span>
              {obs}
            </div>
          ))}
        </div>
      )}

      {/* Rating */}
      <div className="flex items-center gap-2 border-t border-border-subtle pt-3">
        <span className="text-xs text-text-muted">Rate this report</span>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => handleRate(n)}
              className={cn(
                "transition-all",
                n <= (rated ?? 0) ? "text-amber-400" : "text-text-muted hover:text-amber-400/50"
              )}
            >
              <Star className="w-4 h-4" fill={n <= (rated ?? 0) ? "currentColor" : "none"} />
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const [period, setPeriod] = useState<7 | 30>(7);
  const [generating, setGenerating] = useState(false);

  const { data: analytics } = useSWR("analytics", analyticsApi.getSummary);
  const { data: report, mutate: mutateReport } = useSWR(
    "today-report",
    () => reportsApi.generate({ report_date: todayISO() }).catch(() => null)
  );

  async function handleRegenerate() {
    setGenerating(true);
    try {
      await reportsApi.generate({ force_regenerate: true });
      await mutateReport();
    } catch {}
    setGenerating(false);
  }

  const stagger = {
    visible: { transition: { staggerChildren: 0.07 } },
  };
  const fadeUp = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
  };

  return (
    <div className="px-4 pt-12 pb-4 max-w-md mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Insights</h1>
          <p className="text-text-muted text-sm">AI-powered behavioral analytics</p>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={generating}
          className="flex items-center gap-1.5 text-xs text-indigo-400
                     bg-indigo-500/10 border border-indigo-500/20
                     rounded-xl px-3 py-2 hover:bg-indigo-500/15 transition-colors
                     disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", generating && "animate-spin")} />
          Regenerate
        </button>
      </div>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
        className="space-y-4"
      >
        {/* Streak hero */}
        {analytics?.streak && (
          <motion.div
            variants={fadeUp}
            className="card-surface p-4 flex items-center gap-4"
          >
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-4xl"
            >
              🔥
            </motion.div>
            <div>
              <p className="text-2xl font-bold tabular-nums">
                {analytics.streak.current_streak_days}
                <span className="text-sm text-text-muted font-normal"> day streak</span>
              </p>
              <p className="text-xs text-text-muted mt-0.5">
                Best: {analytics.streak.longest_streak_days} days
                {" · "}
                {analytics.streak.is_active_today ? "✓ Logged today" : "Log today to continue"}
              </p>
            </div>
          </motion.div>
        )}

        {/* Consistency scores */}
        {analytics && (
          <motion.div variants={fadeUp} className="card-surface p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-text-secondary">Consistency</h3>
              <div className="flex gap-1 bg-surface-elevated rounded-lg p-0.5">
                {([7, 30] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPeriod(p)}
                    className={cn(
                      "px-2.5 py-1 rounded-md text-xs font-medium transition-all",
                      period === p
                        ? "bg-surface text-text-primary shadow"
                        : "text-text-muted hover:text-text-secondary"
                    )}
                  >
                    {p}d
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-around">
              {[
                { key: "overall_score", label: "Overall" },
                { key: "logging_consistency", label: "Logging" },
                { key: "calorie_adherence", label: "Calories" },
                { key: "protein_adherence", label: "Protein" },
              ].map(({ key, label }) => {
                const data = period === 7 ? analytics.consistency_7d : analytics.consistency_30d;
                return (
                  <ConsistencyRing
                    key={key}
                    score={(data as any)[key]}
                    label={label}
                  />
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Calorie trend chart */}
        <motion.div variants={fadeUp}>
          <TrendChart period={30} />
        </motion.div>

        {/* Pattern insights */}
        {analytics?.pattern_insights?.length ? (
          <motion.div variants={fadeUp}>
            <AIInsightCard
              insights={analytics.pattern_insights}
              className="border-emerald-500/20"
            />
          </motion.div>
        ) : null}

        {/* Meal patterns */}
        {analytics?.meal_patterns?.length ? (
          <motion.div variants={fadeUp} className="card-surface p-4">
            <h3 className="text-sm font-semibold text-text-secondary mb-1">Meal Patterns</h3>
            <p className="text-xs text-text-muted mb-4">How often you log each meal</p>
            <div className="divide-y divide-border-subtle">
              {analytics.meal_patterns.map((mp) => (
                <MealPatternRow key={mp.meal_type} {...mp} />
              ))}
            </div>
          </motion.div>
        ) : null}

        {/* AI Estimation accuracy */}
        {analytics?.estimation_accuracy && (
          <motion.div variants={fadeUp} className="card-surface p-4">
            <h3 className="text-sm font-semibold text-text-secondary mb-3">AI Accuracy</h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <p className="text-xl font-bold tabular-nums text-text-primary">
                  {analytics.estimation_accuracy.total_logs}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Total logs</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold tabular-nums text-emerald-400">
                  {100 - Math.round(analytics.estimation_accuracy.correction_rate_pct)}%
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Accurate</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold tabular-nums text-blue-400">
                  {Math.round(analytics.estimation_accuracy.avg_calorie_delta)}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5">Avg delta</p>
              </div>
            </div>
            {/* Source breakdown */}
            <div className="mt-3 space-y-1.5">
              {Object.entries(analytics.estimation_accuracy.source_breakdown).map(([src, count]) => (
                <div key={src} className="flex items-center gap-2 text-xs">
                  <span className="text-text-muted w-20 capitalize">{src.replace("_", " ")}</span>
                  <div className="flex-1 h-1 bg-surface-elevated rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500/50 rounded-full"
                      style={{
                        width: `${(count / analytics.estimation_accuracy.total_logs) * 100}%`
                      }}
                    />
                  </div>
                  <span className="text-text-muted w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Daily report */}
        {report && (
          <motion.div variants={fadeUp}>
            <DailyReportCard report={report} />
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

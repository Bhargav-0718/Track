"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from "recharts";
import { format, subDays, parseISO } from "date-fns";
import useSWR, { mutate } from "swr";
import { Footprints, Flame, MapPin, Heart, Target } from "lucide-react";

import { ProgressRing } from "@/components/shared/ProgressRing";
import { activityApi, calculateBmr, stepsToKm, stepsToCalories } from "@/lib/api/activity";
import { useAuthStore } from "@/lib/store/auth";
import { cn } from "@/lib/utils/format";
import type { StepLog } from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function todayStr() {
  return format(new Date(), "yyyy-MM-dd");
}

function fmt(n: number) {
  return n.toLocaleString();
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatChip({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div
      className="flex-1 flex flex-col items-center gap-1 rounded-2xl p-3"
      style={{ background: `${color}12`, border: `1px solid ${color}25` }}
    >
      <Icon className="w-4 h-4" style={{ color }} />
      <span className="text-xs font-bold tabular-nums" style={{ color }}>
        {value}
      </span>
      <span className="text-[10px] text-text-muted">{label}</span>
    </div>
  );
}

// ── Custom bar chart tooltip ───────────────────────────────────────────────────

function StepsTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-xl px-3 py-2 text-xs shadow-lg">
      <p className="text-text-muted mb-1">{label}</p>
      <p className="font-bold text-text-primary">{fmt(payload[0].value)} steps</p>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ActivityPage() {
  const { user } = useAuthStore();
  const [stepsInput, setStepsInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // User stats
  const weightKg = user?.weight_kg ?? 70;
  const heightCm = user?.height_cm ?? 170;
  const age = user?.age ?? 25;
  const gender = user?.gender ?? "other";
  const stepsTarget = user?.daily_steps_target ?? 10000;

  // BMR
  const bmr = calculateBmr(weightKg, heightCm, age, gender);

  // Step history
  const { data: historyData, isLoading } = useSWR(
    "step-history",
    () => activityApi.getHistory(7),
    { refreshInterval: 0 }
  );

  const logs: StepLog[] = historyData?.items ?? [];

  // Today's entry
  const today = todayStr();
  const todayLog = logs.find((l) => l.date === today);
  const todaySteps = todayLog?.steps ?? 0;
  const progress = Math.min(todaySteps / stepsTarget, 1);
  const distanceKm = stepsToKm(todaySteps, heightCm);
  const activeCal = stepsToCalories(todaySteps, weightKg, heightCm);
  const totalBurned = bmr + activeCal;

  // Pre-fill input with today's steps
  const [prefilled, setPrefilled] = useState(false);
  if (!prefilled && todaySteps > 0 && stepsInput === "") {
    setStepsInput(todaySteps.toString());
    setPrefilled(true);
  }

  // Build 7-day chart data
  const chartData = Array.from({ length: 7 }, (_, i) => {
    const d = format(subDays(new Date(), 6 - i), "yyyy-MM-dd");
    const log = logs.find((l) => l.date === d);
    return {
      day: i === 6 ? "Today" : format(subDays(new Date(), 6 - i), "EEE"),
      steps: log?.steps ?? 0,
      hitTarget: (log?.steps ?? 0) >= stepsTarget,
    };
  });

  // Weekly stats
  const totalSteps = logs.reduce((s, l) => s + l.steps, 0);
  const avgSteps = logs.length ? Math.round(totalSteps / logs.length) : 0;
  const totalKm = stepsToKm(totalSteps, heightCm);
  const totalCal = stepsToCalories(totalSteps, weightKg, heightCm);
  const daysHit = logs.filter((l) => l.steps >= stepsTarget).length;

  const handleSave = async () => {
    const steps = parseInt(stepsInput, 10);
    if (isNaN(steps) || steps <= 0) return;
    setSaving(true);
    try {
      await activityApi.logSteps(steps);
      await mutate("step-history");
      setSavedMsg(`${fmt(steps)} steps saved!`);
      setTimeout(() => setSavedMsg(""), 3000);
    } catch {
      setSavedMsg("Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const stagger = { visible: { transition: { staggerChildren: 0.07 } } };
  const fadeUp = {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

  return (
    <div className="px-4 pt-12 pb-28 space-y-5 max-w-md mx-auto">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-text-primary">Activity</h1>
        <p className="text-sm text-text-muted mt-0.5">
          Target: <span className="text-emerald-400 font-semibold">{fmt(stepsTarget)} steps/day</span>
        </p>
      </motion.div>

      <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-4">

        {/* ── Today's ring card ──────────────────────────────────────────────── */}
        <motion.div variants={fadeUp} className="card-surface p-5">
          <div className="flex flex-col items-center gap-5">
            <ProgressRing value={progress * 100} size={140} strokeWidth={10} color="#10b981">
              <div className="text-center">
                <p className="text-2xl font-bold tabular-nums text-text-primary">
                  {fmt(todaySteps)}
                </p>
                <p className="text-[10px] text-text-muted">steps</p>
                <p className="text-xs font-semibold text-emerald-400 mt-0.5">
                  {Math.round(progress * 100)}%
                </p>
              </div>
            </ProgressRing>

            {/* Stat chips */}
            <div className="flex gap-2 w-full">
              <StatChip
                icon={MapPin}
                label="Distance"
                value={`${distanceKm.toFixed(2)} km`}
                color="#3b82f6"
              />
              <StatChip
                icon={Footprints}
                label="Active cal"
                value={`${Math.round(activeCal)} kcal`}
                color="#f59e0b"
              />
              <StatChip
                icon={Flame}
                label="Total burn"
                value={`${Math.round(totalBurned)} kcal`}
                color="#8b5cf6"
              />
            </div>
          </div>
        </motion.div>

        {/* ── Log steps ─────────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp} className="card-surface p-4">
          <p className="text-xs text-text-muted font-medium mb-3">LOG TODAY'S STEPS</p>
          <div className="flex gap-3 items-center">
            <div className="flex-1 flex items-center gap-2 bg-surface-elevated border border-border rounded-xl px-4 py-3 focus-within:border-emerald-500/50 transition-colors">
              <Footprints className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <input
                ref={inputRef}
                type="number"
                value={stepsInput}
                onChange={(e) => setStepsInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
                placeholder="e.g. 8500"
                className="flex-1 bg-transparent text-lg font-bold text-text-primary placeholder:text-text-muted outline-none tabular-nums"
              />
              <span className="text-xs text-text-muted">steps</span>
            </div>
            <button
              onClick={handleSave}
              disabled={saving || !stepsInput}
              className={cn(
                "px-5 py-3 rounded-xl text-sm font-semibold transition-all",
                "bg-emerald-500 text-white hover:bg-emerald-400 shadow-glow-emerald",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {saving ? "…" : "Save"}
            </button>
          </div>
          {savedMsg && (
            <motion.p
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "text-xs mt-2",
                savedMsg.includes("Failed") ? "text-rose-400" : "text-emerald-400"
              )}
            >
              {savedMsg}
            </motion.p>
          )}
        </motion.div>

        {/* ── 7-day bar chart ────────────────────────────────────────────────── */}
        {!isLoading && (
          <motion.div variants={fadeUp} className="card-surface p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-secondary">Last 7 Days</h2>
              <span className="text-[10px] text-text-muted">
                Dashed line = {fmt(stepsTarget)} target
              </span>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={chartData} barSize={24}>
                <CartesianGrid
                  vertical={false}
                  stroke="rgba(255,255,255,0.04)"
                />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis hide />
                <Tooltip content={<StepsTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <ReferenceLine
                  y={stepsTarget}
                  stroke="#10b981"
                  strokeDasharray="5 3"
                  strokeOpacity={0.5}
                  label={{ value: "target", position: "insideTopRight", fontSize: 9, fill: "#10b981" }}
                />
                <Bar dataKey="steps" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={
                        entry.hitTarget
                          ? "#10b981"
                          : i === 6
                          ? "#3b82f6"
                          : "rgba(16,185,129,0.25)"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* ── Weekly stats ───────────────────────────────────────────────────── */}
        {logs.length > 0 && (
          <motion.div variants={fadeUp} className="grid grid-cols-4 gap-2">
            {[
              { label: "Avg steps", value: fmt(avgSteps) },
              { label: "Total km", value: totalKm.toFixed(1) },
              { label: "Cal burned", value: fmt(Math.round(totalCal)) },
              {
                label: "Goal days",
                value: `${daysHit}/${logs.length}`,
                highlight: daysHit >= Math.ceil(logs.length / 2),
              },
            ].map(({ label, value, highlight }) => (
              <div key={label} className="card-surface p-3 text-center">
                <p
                  className={cn(
                    "text-sm font-bold tabular-nums",
                    highlight ? "text-emerald-400" : "text-text-primary"
                  )}
                >
                  {value}
                </p>
                <p className="text-[10px] text-text-muted mt-0.5 leading-tight">{label}</p>
              </div>
            ))}
          </motion.div>
        )}

        {/* ── BMR info card ──────────────────────────────────────────────────── */}
        <motion.div
          variants={fadeUp}
          className="flex items-start gap-3 p-4 rounded-2xl"
          style={{ background: "rgba(139,92,246,0.08)", border: "1px solid rgba(139,92,246,0.2)" }}
        >
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(139,92,246,0.15)" }}
          >
            <Heart className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary">
              {Math.round(bmr)} kcal/day resting burn
            </p>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">
              Your body burns this just existing — breathing, heart, organs.
              Steps add on top. Combined = <span className="text-violet-400 font-medium">{Math.round(totalBurned)} kcal</span> total today.
            </p>
            {!user?.gender && (
              <p className="text-[10px] text-amber-400 mt-1.5">
                ⚠️ Set your gender in Profile for a more accurate BMR calculation.
              </p>
            )}
          </div>
        </motion.div>

        {/* ── Set target prompt ──────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <div className="flex items-center justify-between card-surface px-4 py-3.5">
            <div className="flex items-center gap-3">
              <Target className="w-4 h-4 text-emerald-400" />
              <div>
                <p className="text-sm font-medium text-text-primary">Daily Steps Target</p>
                <p className="text-xs text-text-muted">{fmt(stepsTarget)} steps</p>
              </div>
            </div>
            <a
              href="/profile"
              className="text-xs text-emerald-400 font-medium hover:text-emerald-300 transition-colors"
            >
              Change in Profile →
            </a>
          </div>
        </motion.div>

      </motion.div>
    </div>
  );
}

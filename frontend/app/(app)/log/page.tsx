"use client";

import {
  useState, useRef, useId,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, X, ChevronDown, ChevronUp,
  Trash2, Dumbbell, Flame, Check, Plus, History,
  Bike, BedDouble, Smartphone,
} from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { format } from "date-fns";
import { useSearchParams, useRouter } from "next/navigation";

import { foodApi } from "@/lib/api/food";
import { workoutApi } from "@/lib/api/workout";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import {
  formatCalories, formatGrams, formatMealType,
  getSourceInfo, todayISO, MEAL_LABELS, cn
} from "@/lib/utils/format";
import type {
  FoodLog, MealType, WorkoutLog, WorkoutType,
  CardioActivityInput, StrengthExerciseInput, WorkoutSection,
} from "@/lib/types";

// ── Constants ─────────────────────────────────────────────────────────────────

const MEAL_ORDER: MealType[] = [
  "breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"
];

const WORKOUT_TYPES: { value: WorkoutType; label: string }[] = [
  { value: "strength", label: "Strength" },
  { value: "cardio",   label: "Cardio"   },
  { value: "hiit",     label: "HIIT"     },
  { value: "yoga",     label: "Yoga"     },
  { value: "sports",   label: "Sports"   },
  { value: "other",    label: "Other"    },
];

// ── Food helpers ──────────────────────────────────────────────────────────────

interface MealGroup {
  id: string;           // meal_group_id for compound, log.id for singles
  raw_input: string | null;
  meal_type: MealType;
  logs: FoodLog[];
  total_calories: number;
  total_protein_g: number | null;
  total_carbs_g: number | null;
  total_fat_g: number | null;
  is_compound: boolean;
}

function buildMealGroups(logs: FoodLog[]): MealGroup[] {
  const map = new Map<string, MealGroup>();
  for (const log of logs) {
    const key = log.meal_group_id ?? log.id;
    if (!map.has(key)) {
      map.set(key, {
        id: key,
        raw_input: log.raw_input,
        meal_type: log.meal_type,
        logs: [],
        total_calories: 0,
        total_protein_g: null,
        total_carbs_g: null,
        total_fat_g: null,
        is_compound: log.meal_group_id != null,
      });
    }
    const g = map.get(key)!;
    g.logs.push(log);
    g.total_calories += log.calories;
    if (log.protein_g != null) g.total_protein_g = (g.total_protein_g ?? 0) + log.protein_g;
    if (log.carbs_g != null)   g.total_carbs_g   = (g.total_carbs_g   ?? 0) + log.carbs_g;
    if (log.fat_g != null)     g.total_fat_g     = (g.total_fat_g     ?? 0) + log.fat_g;
  }
  return Array.from(map.values());
}

function groupByMeal(groups: MealGroup[]): Record<string, MealGroup[]> {
  const result: Record<string, MealGroup[]> = {};
  for (const g of groups) {
    if (!result[g.meal_type]) result[g.meal_type] = [];
    result[g.meal_type].push(g);
  }
  return result;
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

function TabBar({
  active,
  onChange,
}: {
  active: "food" | "workout";
  onChange: (t: "food" | "workout") => void;
}) {
  return (
    <div className="flex bg-surface border border-border rounded-xl p-1 gap-1">
      {(["food", "workout"] as const).map((tab) => {
        const isActive = active === tab;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[13px] font-medium transition-all duration-200",
              isActive
                ? "bg-emerald-500 text-white shadow-sm"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            <span>{tab === "food" ? "🍽" : "💪"}</span>
            {tab === "food" ? "Food" : "Workout"}
          </button>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FOOD TAB
// ─────────────────────────────────────────────────────────────────────────────

function ComponentRow({
  log,
  onDelete,
}: {
  log: FoodLog;
  onDelete: (id: string) => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await foodApi.deleteLog(log.id);
      onDelete(log.id);
    } catch {
      setDeleting(false);
    }
  }

  const qty = log.quantity ?? 1;
  const perUnit = log.calories_per_unit;

  return (
    <div className="flex items-center gap-2 py-2 border-b border-border-subtle last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary capitalize">{log.food_name}</p>
        {perUnit != null && qty > 1 && (
          <p className="text-[11px] text-text-muted tabular-nums mt-0.5">
            × {qty % 1 === 0 ? qty.toFixed(0) : qty} · {Math.round(perUnit)} kcal/unit
          </p>
        )}
      </div>
      <p className="text-sm font-semibold tabular-nums text-text-primary shrink-0">
        {Math.round(log.calories)} kcal
      </p>
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="p-1 text-text-muted hover:text-red-400 transition-colors disabled:opacity-40 shrink-0"
      >
        {deleting
          ? <div className="w-3 h-3 border border-red-400/50 border-t-red-400 rounded-full animate-spin" />
          : <Trash2 className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}

function MealGroupCard({ group, onDelete }: { group: MealGroup; onDelete: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);

  const firstLog = group.logs[0];
  const confidenceColor =
    firstLog.confidence_level === "confirmed"
      ? "bg-emerald-500"
      : firstLog.confidence_level === "estimated"
      ? "bg-amber-500"
      : "bg-text-muted";

  const groupLabel = group.is_compound
    ? group.logs.map((l) => l.food_name).join(" · ")
    : firstLog.food_name;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20, height: 0 }}
      className="card-surface overflow-hidden mb-2"
    >
      {/* Header row */}
      <div className="flex items-center px-4 py-3.5 gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary truncate capitalize">{groupLabel}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", confidenceColor)} />
            <span className="text-xs text-text-muted">{formatMealType(firstLog.meal_type)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-sm font-bold tabular-nums">
            {Math.round(group.total_calories)} kcal
          </p>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-text-muted hover:text-text-secondary transition-colors p-1"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-border-subtle px-4 py-3 space-y-3"
          >
            {/* Component breakdown */}
            <div>
              {group.logs.map((log) => (
                <ComponentRow key={log.id} log={log} onDelete={onDelete} />
              ))}
            </div>

            {/* Macro totals */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Protein", value: group.total_protein_g, color: "text-blue-400" },
                { label: "Carbs",   value: group.total_carbs_g,   color: "text-amber-400" },
                { label: "Fat",     value: group.total_fat_g,     color: "text-violet-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-surface-elevated rounded-xl p-2.5 text-center">
                  <p className={cn("text-sm font-bold tabular-nums", color)}>{formatGrams(value)}</p>
                  <p className="text-[10px] text-text-muted">{label}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function FoodTab({ onLogged, onDelete, daily }: {
  onLogged: () => void;
  onDelete: (id: string) => void;
  daily: ReturnType<typeof useSWR<any>>["data"];
}) {
  const [query, setQuery] = useState("");
  const [mealType, setMealType] = useState<MealType>("lunch");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const logs = await foodApi.createLog({ raw_input: query.trim(), meal_type: mealType });
      const totalKcal = logs.reduce((s, l) => s + l.calories, 0);
      const label = logs.length === 1
        ? logs[0].food_name
        : logs.map((l) => l.food_name).join(" + ");
      setResult(`${label} — ${Math.round(totalKcal)} kcal logged!`);
      setQuery("");
      onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log food");
    } finally {
      setLoading(false);
    }
  }

  const mealGroups = buildMealGroups(daily?.logs ?? []);
  const groups = groupByMeal(mealGroups);
  const orderedMeals = MEAL_ORDER.filter((m) => groups[m]?.length);

  return (
    <div className="space-y-6">
      {/* Input card */}
      <div className="card-surface p-4 space-y-4">
        <div>
          <p className="text-base font-bold">Log Food</p>
          <p className="text-sm text-text-secondary mt-0.5">
            Describe what you ate — AI estimates nutrition automatically.
          </p>
        </div>

        {/* Meal type chips */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {MEAL_ORDER.map((type) => (
            <button
              key={type}
              onClick={() => setMealType(type)}
              className={cn(
                "shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all border",
                mealType === type
                  ? "bg-emerald-500 text-white border-emerald-500"
                  : "bg-surface-elevated text-text-secondary border-border"
              )}
            >
              {MEAL_LABELS[type]}
            </button>
          ))}
        </div>

        {/* Text input */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <textarea
            ref={inputRef}
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "2 rotis with dal and sabzi" or "protein shake 30g"'
            className="w-full bg-surface border border-border rounded-xl
                       px-4 py-3 text-sm text-text-primary resize-none
                       placeholder:text-text-muted
                       focus:outline-none focus:border-emerald-500/50
                       transition-all duration-200"
            disabled={loading}
          />

          {/* Success */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 bg-emerald-500/10 rounded-xl px-3 py-2.5"
              >
                <Check className="w-4 h-4 text-emerald-400 shrink-0" strokeWidth={2.5} />
                <p className="text-sm text-emerald-400">{result}</p>
              </motion.div>
            )}
            {error && (
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-red-400 text-sm">
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="w-full py-3 rounded-xl bg-emerald-500 text-white text-sm font-semibold
                       hover:bg-emerald-600 transition-colors disabled:opacity-40
                       flex items-center justify-center gap-2"
          >
            {loading
              ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : <Sparkles className="w-4 h-4" />}
            {loading ? "Estimating…" : "Estimate & Log"}
          </button>
        </form>
      </div>

      {/* Today's entries */}
      <div>
        <p className="text-[15px] font-semibold mb-2.5">Today's Entries</p>
        {orderedMeals.length === 0 ? (
          <p className="text-center text-text-muted py-8 text-sm">No entries yet.</p>
        ) : (
          orderedMeals.map((mealType) => (
            <div key={mealType} className="mb-4">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                  {formatMealType(mealType)}
                </p>
                <p className="text-xs text-text-muted tabular-nums">
                  {formatCalories(groups[mealType].reduce((s, g) => s + g.total_calories, 0))} kcal
                </p>
              </div>
              <AnimatePresence>
                {groups[mealType].map((group) => (
                  <MealGroupCard key={group.id} group={group} onDelete={onDelete} />
                ))}
              </AnimatePresence>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKOUT TAB — 3 sections: App Workout / Cardio / Strength
// ─────────────────────────────────────────────────────────────────────────────

const WORKOUT_SECTIONS: { value: WorkoutSection; label: string; icon: React.ReactNode }[] = [
  { value: "app_workout", label: "App Workout", icon: <Smartphone className="w-3.5 h-3.5" /> },
  { value: "cardio",      label: "Cardio",      icon: <Bike className="w-3.5 h-3.5" /> },
  { value: "strength",    label: "Strength",    icon: <Dumbbell className="w-3.5 h-3.5" /> },
];

// ── Rest day toggle ────────────────────────────────────────────────────────────

function RestDayToggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-medium transition-all",
        checked
          ? "bg-slate-500/20 text-slate-300 border-slate-500/40"
          : "bg-surface-elevated text-text-muted border-border"
      )}
    >
      <BedDouble className="w-3.5 h-3.5" />
      Rest day
    </button>
  );
}

// ── Input helpers ──────────────────────────────────────────────────────────────

function FieldInput({
  value, onChange, placeholder, type = "text", className = "",
}: {
  value: string; onChange: (v: string) => void;
  placeholder: string; type?: string; className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        "bg-surface border border-border rounded-xl px-3 py-2.5 text-sm text-text-primary",
        "placeholder:text-text-muted focus:outline-none focus:border-blue-500/50 transition-all",
        className,
      )}
    />
  );
}

// ── Section: App Workout ───────────────────────────────────────────────────────

function AppWorkoutSection({
  onLogged, recentWorkouts,
}: { onLogged: () => void; recentWorkouts: WorkoutLog[] }) {
  const [calories, setCalories] = useState("");
  const [isRest, setIsRest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleLog(e: React.FormEvent) {
    e.preventDefault();
    if (!isRest && !calories.trim()) return;
    setLoading(true);
    setSuccess(null);
    try {
      const logs = await workoutApi.createSectionedLog({
        section: isRest ? "rest_day" : "app_workout",
        is_rest_day: isRest,
        calories_from_app: isRest ? undefined : parseFloat(calories) || 0,
      });
      const totalKcal = logs.reduce((s, l) => s + (l.calories_burned ?? 0), 0);
      setSuccess(isRest ? "Rest day logged!" : `${Math.round(totalKcal)} kcal logged!`);
      setCalories("");
      setIsRest(false);
      onLogged();
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleLog} className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">Calories shown in your app / watch</p>
        <RestDayToggle checked={isRest} onChange={setIsRest} />
      </div>

      {!isRest && (
        <div className="flex items-center gap-3 bg-surface-elevated border border-border rounded-xl p-3.5">
          <Flame className="w-5 h-5 text-amber-400 shrink-0" />
          <input
            type="number"
            value={calories}
            onChange={(e) => setCalories(e.target.value)}
            placeholder="450"
            min={0}
            className="flex-1 bg-transparent text-[22px] font-bold text-text-primary
                       placeholder:text-text-muted focus:outline-none"
          />
          <p className="text-xs text-text-muted shrink-0">kcal</p>
        </div>
      )}

      <AnimatePresence>
        {success && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 bg-emerald-500/10 rounded-xl px-3 py-2.5">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" strokeWidth={2.5} />
            <p className="text-sm text-emerald-400">{success}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <button type="submit" disabled={loading || (!isRest && !calories.trim())}
        className="w-full py-3 rounded-xl bg-blue-500 text-white text-sm font-semibold
                   hover:bg-blue-600 transition-colors disabled:opacity-40
                   flex items-center justify-center gap-2">
        {loading
          ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <Flame className="w-4 h-4" />}
        {loading ? "Logging…" : isRest ? "Log Rest Day" : "Log Workout"}
      </button>
    </form>
  );
}

// ── Section: Cardio ────────────────────────────────────────────────────────────

interface CardioRow { id: string; activity: string; duration: string; calories: string; }
function newCardioRow(id: string): CardioRow { return { id, activity: "", duration: "", calories: "" }; }

function CardioSection({ onLogged }: { onLogged: () => void }) {
  const [rows, setRows] = useState<CardioRow[]>([newCardioRow("0")]);
  const [nextId, setNextId] = useState(1);
  const [isRest, setIsRest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function addRow() { setRows((r) => [...r, newCardioRow(String(nextId))]); setNextId((n) => n + 1); }
  function removeRow(id: string) { if (rows.length > 1) setRows((r) => r.filter((row) => row.id !== id)); }
  function update(id: string, field: keyof Omit<CardioRow, "id">, val: string) {
    setRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }

  async function handleLog(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setSuccess(null);
    setError(null);
    try {
      if (isRest) {
        await workoutApi.createSectionedLog({ section: "rest_day", is_rest_day: true });
        setSuccess("Rest day logged!");
        onLogged();
        return;
      }
      const valid = rows.filter((r) => r.activity.trim() && r.duration.trim());
      if (!valid.length) return;
      const activities: CardioActivityInput[] = valid.map((r) => ({
        activity_description: r.activity.trim(),
        duration_minutes: parseFloat(r.duration) || 0,
        ...(r.calories.trim() ? { calories_burned: parseFloat(r.calories) } : {}),
      }));
      const logs = await workoutApi.createSectionedLog({ section: "cardio", cardio_activities: activities });
      const totalKcal = logs.reduce((s, l) => s + (l.calories_burned ?? 0), 0);
      setSuccess(`${logs.length} activit${logs.length !== 1 ? "ies" : "y"} logged · ${Math.round(totalKcal)} kcal`);
      setRows([newCardioRow(String(nextId))]);
      setNextId((n) => n + 1);
      onLogged();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? "Failed to log cardio — check your connection");
    } finally {
      setLoading(false);
    }
  }

  const hasAiEstimate = !isRest && rows.some((r) => r.activity.trim() && r.duration.trim() && !r.calories.trim());

  return (
    <form onSubmit={handleLog} className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">
          Omit calories to let AI estimate from your weight + activity.
        </p>
        <RestDayToggle checked={isRest} onChange={setIsRest} />
      </div>

      {!isRest && (
        <div className="space-y-2">
          {/* Column headers */}
          <div className="flex gap-2 px-1">
            <p className="flex-[5] text-[11px] text-text-muted">Activity</p>
            <p className="w-14 text-center text-[11px] text-text-muted">Min</p>
            <p className="w-16 text-center text-[11px] text-text-muted">kcal (opt)</p>
            <div className="w-7" />
          </div>

          <AnimatePresence initial={false}>
            {rows.map((row) => (
              <motion.div key={row.id}
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                className="flex gap-2 items-center">
                <FieldInput value={row.activity} onChange={(v) => update(row.id, "activity", v)}
                  placeholder="Treadmill walk, Cycling…" className="flex-[5]" />
                <FieldInput value={row.duration} onChange={(v) => update(row.id, "duration", v)}
                  placeholder="10" type="number" className="w-14 text-center" />
                <FieldInput value={row.calories} onChange={(v) => update(row.id, "calories", v)}
                  placeholder="—" type="number" className="w-16 text-center" />
                <button type="button" onClick={() => removeRow(row.id)}
                  className={cn("w-7 h-7 flex items-center justify-center rounded-lg transition-colors",
                    rows.length === 1 ? "opacity-20 cursor-not-allowed" : "text-text-muted hover:text-red-400"
                  )} disabled={rows.length === 1}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          <button type="button" onClick={addRow}
            className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium hover:text-blue-300 transition-colors py-1">
            <Plus className="w-4 h-4" /> Add activity
          </button>
        </div>
      )}

      <AnimatePresence>
        {loading && hasAiEstimate && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-3 bg-blue-500/10 border border-blue-500/20 rounded-xl px-3 py-2.5">
            <div className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin shrink-0" />
            <p className="text-sm text-blue-300">AI is estimating calories for your activities…</p>
          </motion.div>
        )}
        {success && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 bg-emerald-500/10 rounded-xl px-3 py-2.5">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" strokeWidth={2.5} />
            <p className="text-sm text-emerald-400">{success}</p>
          </motion.div>
        )}
        {error && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2.5">
            <X className="w-4 h-4 text-rose-400 shrink-0" />
            <p className="text-sm text-rose-400">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <button type="submit"
        disabled={loading || (!isRest && rows.every((r) => !r.activity.trim() || !r.duration.trim()))}
        className="w-full py-3 rounded-xl bg-blue-500 text-white text-sm font-semibold
                   hover:bg-blue-600 transition-colors disabled:opacity-40
                   flex items-center justify-center gap-2">
        {loading
          ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <Bike className="w-4 h-4" />}
        {loading ? "Estimating…" : isRest ? "Log Rest Day" : "Log Cardio"}
      </button>
    </form>
  );
}

// ── Section: Strength ──────────────────────────────────────────────────────────

interface StrRow { id: string; name: string; sets: string; reps: string; weight: string; }
function newStrRow(id: string): StrRow { return { id, name: "", sets: "", reps: "", weight: "" }; }

function ExerciseAutocomplete({
  value, onChange, history, placeholder,
}: { value: string; onChange: (v: string) => void; history: string[]; placeholder: string }) {
  const [open, setOpen] = useState(false);
  const suggestions = open && value.length > 0
    ? history.filter((n) => n.toLowerCase().includes(value.toLowerCase())).slice(0, 6)
    : [];
  return (
    <div className="relative flex-[5] min-w-0">
      <input
        type="text"
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full bg-surface border border-border rounded-xl px-3 py-2.5 text-sm text-text-primary
                   placeholder:text-text-muted focus:outline-none focus:border-blue-500/50 transition-all"
      />
      {open && suggestions.length > 0 && (
        <div className="absolute left-0 top-full mt-1 z-50 bg-surface-elevated border border-border
                        rounded-xl overflow-hidden shadow-lg w-52">
          {suggestions.map((s) => (
            <button key={s} type="button" onMouseDown={() => { onChange(s); setOpen(false); }}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-text-primary
                         hover:bg-surface transition-colors text-left">
              <History className="w-3.5 h-3.5 text-text-muted shrink-0" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function StrengthSection({ onLogged, recentWorkouts }: { onLogged: () => void; recentWorkouts: WorkoutLog[] }) {
  const [rows, setRows] = useState<StrRow[]>([newStrRow("0")]);
  const [nextId, setNextId] = useState(1);
  const [isRest, setIsRest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const exerciseHistory: string[] = Array.from(
    new Set(recentWorkouts
      .filter((w) => w.workout_section === "strength")
      .flatMap((w) => w.exercises.map((e: any) => e.name as string).filter(Boolean))
    )
  ).sort();

  function addRow() { setRows((r) => [...r, newStrRow(String(nextId))]); setNextId((n) => n + 1); }
  function removeRow(id: string) { if (rows.length > 1) setRows((r) => r.filter((row) => row.id !== id)); }
  function update(id: string, field: keyof Omit<StrRow, "id">, val: string) {
    setRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }

  async function handleLog(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setSuccess(null);
    try {
      if (isRest) {
        await workoutApi.createSectionedLog({ section: "rest_day", is_rest_day: true });
        setSuccess("Rest day logged!");
        onLogged();
        return;
      }
      const valid = rows.filter((r) => r.name.trim() && r.sets.trim() && r.reps.trim());
      if (!valid.length) return;
      const exercises: StrengthExerciseInput[] = valid.map((r) => ({
        name: r.name.trim(),
        sets: parseInt(r.sets) || 1,
        reps: parseInt(r.reps) || 1,
        weight_kg: parseFloat(r.weight) || 0,
      }));
      const logs = await workoutApi.createSectionedLog({ section: "strength", strength_exercises: exercises });
      const totalKcal = logs.reduce((s, l) => s + (l.calories_burned ?? 0), 0);
      setSuccess(`${logs.length} exercise${logs.length !== 1 ? "s" : ""} logged · ${Math.round(totalKcal)} kcal`);
      setRows([newStrRow(String(nextId))]);
      setNextId((n) => n + 1);
      onLogged();
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleLog} className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">
          AI estimates calories from your sets × reps × weight.
        </p>
        <RestDayToggle checked={isRest} onChange={setIsRest} />
      </div>

      {!isRest && (
        <div className="space-y-2">
          {/* Column headers */}
          <div className="flex gap-2 px-1">
            <p className="flex-[5] text-[11px] text-text-muted">Exercise</p>
            <p className="w-10 text-center text-[11px] text-text-muted">Sets</p>
            <p className="w-10 text-center text-[11px] text-text-muted">Reps</p>
            <p className="w-14 text-center text-[11px] text-text-muted">kg</p>
            <div className="w-7" />
          </div>

          <AnimatePresence initial={false}>
            {rows.map((row) => (
              <motion.div key={row.id}
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                className="flex gap-2 items-center">
                <ExerciseAutocomplete
                  value={row.name} onChange={(v) => update(row.id, "name", v)}
                  history={exerciseHistory} placeholder="Bench Press, Squat…" />
                <FieldInput value={row.sets} onChange={(v) => update(row.id, "sets", v)}
                  placeholder="3" type="number" className="w-10 text-center" />
                <FieldInput value={row.reps} onChange={(v) => update(row.id, "reps", v)}
                  placeholder="10" type="number" className="w-10 text-center" />
                <FieldInput value={row.weight} onChange={(v) => update(row.id, "weight", v)}
                  placeholder="0" type="number" className="w-14 text-center" />
                <button type="button" onClick={() => removeRow(row.id)}
                  className={cn("w-7 h-7 flex items-center justify-center rounded-lg transition-colors",
                    rows.length === 1 ? "opacity-20 cursor-not-allowed" : "text-text-muted hover:text-red-400"
                  )} disabled={rows.length === 1}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          <button type="button" onClick={addRow}
            className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium hover:text-blue-300 transition-colors py-1">
            <Plus className="w-4 h-4" /> Add exercise
          </button>
        </div>
      )}

      <AnimatePresence>
        {success && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 bg-emerald-500/10 rounded-xl px-3 py-2.5">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" strokeWidth={2.5} />
            <p className="text-sm text-emerald-400">{success}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <button type="submit"
        disabled={loading || (!isRest && rows.every((r) => !r.name.trim()))}
        className="w-full py-3 rounded-xl bg-blue-500 text-white text-sm font-semibold
                   hover:bg-blue-600 transition-colors disabled:opacity-40
                   flex items-center justify-center gap-2">
        {loading
          ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <Dumbbell className="w-4 h-4" />}
        {loading ? "Estimating…" : isRest ? "Log Rest Day" : "Log Strength"}
      </button>
    </form>
  );
}

// ── WorkoutTab orchestrator ────────────────────────────────────────────────────

function WorkoutTab({ onLogged, recentWorkouts, mutateRecent }: {
  onLogged: () => void;
  recentWorkouts: WorkoutLog[];
  mutateRecent: () => void;
}) {
  const [activeSection, setActiveSection] = useState<WorkoutSection>("app_workout");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDeleteWorkout(id: string) {
    setDeletingId(id);
    try {
      await workoutApi.deleteLog(id);
      mutateRecent();
    } catch {
      // non-fatal
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Section selector */}
      <div className="card-surface p-4 space-y-5">
        {/* Section tabs */}
        <div className="flex gap-2">
          {WORKOUT_SECTIONS.map(({ value, label, icon }) => (
            <button key={value} type="button" onClick={() => setActiveSection(value)}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium transition-all border",
                activeSection === value
                  ? "bg-blue-500/20 text-blue-400 border-blue-500/40"
                  : "bg-surface-elevated text-text-secondary border-border"
              )}>
              {icon}
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* Active section form */}
        <AnimatePresence mode="wait">
          <motion.div key={activeSection}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.15 }}>
            {activeSection === "app_workout" && (
              <AppWorkoutSection onLogged={() => { onLogged(); mutateRecent(); }} recentWorkouts={recentWorkouts} />
            )}
            {activeSection === "cardio" && (
              <CardioSection onLogged={() => { onLogged(); mutateRecent(); }} />
            )}
            {activeSection === "strength" && (
              <StrengthSection onLogged={() => { onLogged(); mutateRecent(); }} recentWorkouts={recentWorkouts} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Recent workouts */}
      <div>
        <p className="text-[15px] font-semibold mb-2.5">Recent Workouts</p>
        {recentWorkouts.length === 0 ? (
          <p className="text-center text-text-muted py-8 text-sm">No workouts yet.</p>
        ) : (
          <div className="space-y-2">
            {recentWorkouts.map((log, i) => {
              const sectionIcon =
                log.workout_section === "cardio" ? <Bike className="w-5 h-5 text-blue-400" />
                : log.workout_section === "strength" ? <Dumbbell className="w-5 h-5 text-blue-400" />
                : log.is_rest_day ? <BedDouble className="w-5 h-5 text-slate-400" />
                : <Smartphone className="w-5 h-5 text-blue-400" />;
              return (
                <motion.div key={log.id}
                  initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="card-surface flex items-center gap-3 px-4 py-3.5">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0">
                    {sectionIcon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">{log.title}</p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {log.is_rest_day ? "Rest day"
                        : `${log.workout_section === "cardio" ? "Cardio"
                            : log.workout_section === "strength" ? "Strength"
                            : "App"} · ${log.duration_minutes > 0 ? `${log.duration_minutes} min` : ""}`
                      }
                      {(log.exercises?.length ?? 0) > 0 && !log.is_rest_day && ` · ${log.exercises!.length} item${log.exercises!.length !== 1 ? "s" : ""}`}
                    </p>
                  </div>
                  {log.calories_burned != null && log.calories_burned > 0 && (
                    <p className="text-sm font-semibold text-amber-400 tabular-nums shrink-0">
                      {Math.round(log.calories_burned)} kcal
                    </p>
                  )}
                  <button
                    onClick={() => handleDeleteWorkout(log.id)}
                    disabled={deletingId === log.id}
                    className="ml-1 p-1.5 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-40 shrink-0"
                  >
                    {deletingId === log.id
                      ? <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      : <Trash2 className="w-3.5 h-3.5" />}
                  </button>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────

export default function LogPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { mutate } = useSWRConfig();

  const initialTab = searchParams.get("tab") === "workout" ? "workout" : "food";
  const [activeTab, setActiveTab] = useState<"food" | "workout">(initialTab);

  function switchTab(tab: "food" | "workout") {
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "workout") params.set("tab", "workout");
    else params.delete("tab");
    router.replace(`/log?${params.toString()}`);
  }

  const { data: daily, mutate: mutateDaily } = useSWR(
    ["daily", todayISO()],
    () => foodApi.getDaily(todayISO()),
    { revalidateOnFocus: true }
  );

  const { data: recentWorkoutsResp, mutate: mutateRecentWorkouts } = useSWR(
    "recent-workouts",
    () => workoutApi.getRecent(20),
    { revalidateOnFocus: true }
  );

  const recentWorkouts = recentWorkoutsResp?.items ?? [];

  function handleFoodLogged() {
    mutateDaily();
    mutate("recent-foods");
    mutate("today-report");
    mutate("streak");
  }

  function handleFoodDelete(id: string) {
    mutateDaily(
      (prev: any) => prev ? { ...prev, logs: prev.logs.filter((l: FoodLog) => l.id !== id) } : prev,
      { revalidate: true }
    );
  }

  function handleWorkoutLogged() {
    mutate("today-report");
    mutate("streak");
  }

  return (
    <div className="px-4 pt-12 pb-24 max-w-md mx-auto space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Log</h1>
        <p className="text-text-muted text-sm mt-0.5">
          {format(new Date(), "EEEE, MMMM d")}
        </p>
      </div>

      {/* Tab bar */}
      <TabBar active={activeTab} onChange={switchTab} />

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === "food" ? (
          <motion.div
            key="food"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.18 }}
          >
            <FoodTab
              daily={daily}
              onLogged={handleFoodLogged}
              onDelete={handleFoodDelete}
            />
          </motion.div>
        ) : (
          <motion.div
            key="workout"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.18 }}
          >
            <WorkoutTab
              onLogged={handleWorkoutLogged}
              recentWorkouts={recentWorkouts}
              mutateRecent={() => mutateRecentWorkouts()}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

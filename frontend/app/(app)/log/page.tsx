"use client";

import {
  useState, useRef, useCallback, useId,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Sparkles, X, ChevronDown, ChevronUp,
  Trash2, Clock, Dumbbell, Flame, Check, Plus, History,
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
import type { FoodLog, MealType, WorkoutLog, WorkoutType, Exercise } from "@/lib/types";

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

function groupByMeal(logs: FoodLog[]): Record<string, FoodLog[]> {
  const groups: Record<string, FoodLog[]> = {};
  for (const log of logs) {
    if (!groups[log.meal_type]) groups[log.meal_type] = [];
    groups[log.meal_type].push(log);
  }
  return groups;
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

function FoodLogCard({ log, onDelete }: { log: FoodLog; onDelete: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const sourceInfo = getSourceInfo(log.estimation_source);

  const confidenceColor =
    log.confidence_level === "confirmed"
      ? "bg-emerald-500"
      : log.confidence_level === "estimated"
      ? "bg-amber-500"
      : "bg-text-muted";

  async function handleDelete() {
    setDeleting(true);
    try {
      await foodApi.deleteLog(log.id);
      onDelete(log.id);
    } catch {
      setDeleting(false);
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20, height: 0 }}
      className="card-surface overflow-hidden mb-2"
    >
      <div className="flex items-center px-4 py-3.5 gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary truncate">{log.food_name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", confidenceColor)} />
            <span className="text-xs text-text-muted">{formatMealType(log.meal_type)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-bold tabular-nums">{formatCalories(log.calories)} kcal</p>
            {log.protein_g != null && (
              <p className="text-xs text-text-muted">P: {formatGrams(log.protein_g)}</p>
            )}
          </div>
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
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Protein", value: log.protein_g, color: "text-blue-400" },
                { label: "Carbs",   value: log.carbs_g,   color: "text-amber-400" },
                { label: "Fat",     value: log.fat_g,     color: "text-violet-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-surface-elevated rounded-xl p-2.5 text-center">
                  <p className={cn("text-sm font-bold tabular-nums", color)}>{formatGrams(value)}</p>
                  <p className="text-[10px] text-text-muted">{label}</p>
                </div>
              ))}
            </div>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="w-full flex items-center justify-center gap-1.5 py-2
                         text-xs text-red-400 hover:bg-red-500/10 rounded-xl
                         border border-red-500/20 transition-colors disabled:opacity-50"
            >
              {deleting
                ? <div className="w-3 h-3 border border-red-400/50 border-t-red-400 rounded-full animate-spin" />
                : <Trash2 className="w-3.5 h-3.5" />}
              Delete
            </button>
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
      const log = await foodApi.createLog({ raw_input: query.trim(), meal_type: mealType });
      setResult(`${log.food_name} — ${Math.round(log.calories)} kcal logged!`);
      setQuery("");
      onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log food");
    } finally {
      setLoading(false);
    }
  }

  const groups = groupByMeal(daily?.logs ?? []);
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
                  {formatCalories(groups[mealType].reduce((s, l) => s + l.calories, 0))} kcal
                </p>
              </div>
              <AnimatePresence>
                {groups[mealType].map((log) => (
                  <FoodLogCard key={log.id} log={log} onDelete={onDelete} />
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
// WORKOUT TAB
// ─────────────────────────────────────────────────────────────────────────────

interface ExRow {
  id: string;
  name: string;
  sets: string;
  reps: string;
}

function newRow(id: string): ExRow {
  return { id, name: "", sets: "", reps: "" };
}

function ExerciseAutocomplete({
  value,
  onChange,
  history,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  history: string[];
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const suggestions = open && value.length > 0
    ? history.filter((n) => n.toLowerCase().includes(value.toLowerCase())).slice(0, 6)
    : [];

  return (
    <div className="relative flex-1 min-w-0">
      <input
        type="text"
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full bg-surface border border-border rounded-xl
                   px-3 py-2.5 text-sm text-text-primary
                   placeholder:text-text-muted
                   focus:outline-none focus:border-blue-500/50
                   transition-all duration-200"
      />
      {open && suggestions.length > 0 && (
        <div className="absolute left-0 top-full mt-1 z-50 bg-surface-elevated border border-border
                        rounded-xl overflow-hidden shadow-lg w-56">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onMouseDown={() => { onChange(s); setOpen(false); }}
              className="flex items-center gap-2 w-full px-3 py-2.5 text-sm text-text-primary
                         hover:bg-surface transition-colors text-left"
            >
              <History className="w-3.5 h-3.5 text-text-muted shrink-0" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function WorkoutTab({ onLogged, recentWorkouts, mutateRecent }: {
  onLogged: () => void;
  recentWorkouts: WorkoutLog[];
  mutateRecent: () => void;
}) {
  const [workoutType, setWorkoutType] = useState<WorkoutType>("strength");
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("");
  const [calories, setCalories] = useState("");
  const [rows, setRows] = useState<ExRow[]>([newRow("0")]);
  const [nextId, setNextId] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  // Exercise history from recent workouts
  const exerciseHistory: string[] = Array.from(
    new Set(recentWorkouts.flatMap((w) => w.exercises.map((e) => e.name).filter(Boolean)))
  ).sort();

  function addRow() {
    setRows((r) => [...r, newRow(String(nextId))]);
    setNextId((n) => n + 1);
  }

  function removeRow(id: string) {
    if (rows.length === 1) return;
    setRows((r) => r.filter((row) => row.id !== id));
  }

  function updateRow(id: string, field: keyof Omit<ExRow, "id">, val: string) {
    setRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }

  async function handleLog(e: React.FormEvent) {
    e.preventDefault();
    const validExercises = rows.filter((r) => r.name.trim());
    if (validExercises.length === 0) return;

    setLoading(true);
    setSuccess(null);

    const autoTitle = title.trim() || validExercises.map((e) => e.name.trim()).join(", ");
    const exercises: Exercise[] = validExercises.map((r) => ({
      name: r.name.trim(),
      sets: r.sets ? parseInt(r.sets) : undefined,
      reps: r.reps ? parseInt(r.reps) : undefined,
    }));

    try {
      const w = await workoutApi.createLog({
        title: autoTitle,
        workout_type: workoutType,
        duration_minutes: parseInt(duration) || 30,
        intensity: "moderate",
        exercises,
        ...(calories ? { calories_burned: parseFloat(calories) } : {}),
      });

      const kcalStr = w.calories_burned ? ` ${Math.round(w.calories_burned)} kcal` : "";
      setSuccess(`${w.title} logged!${kcalStr}`);
      setTitle("");
      setDuration("");
      setCalories("");
      setRows([newRow(String(nextId))]);
      setNextId((n) => n + 1);
      onLogged();
      mutateRecent();
    } catch {
      // error silently (matches mobile snackbar pattern)
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Main card */}
      <form onSubmit={handleLog} className="card-surface p-4 space-y-5">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-500/15 flex items-center justify-center">
            <Dumbbell className="w-[18px] h-[18px] text-blue-400" />
          </div>
          <p className="text-base font-bold">Log Workout</p>
        </div>

        {/* Workout type chips */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {WORKOUT_TYPES.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setWorkoutType(value)}
              className={cn(
                "shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all border",
                workoutType === value
                  ? "bg-blue-500/20 text-blue-400 border-blue-500/40"
                  : "bg-surface-elevated text-text-secondary border-border"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Title + Duration row */}
        <div className="flex gap-3">
          <div className="flex-[3] space-y-1.5">
            <p className="text-[13px] text-text-secondary">Session name (optional)</p>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Push day"
              className="w-full bg-surface border border-border rounded-xl
                         px-3 py-2.5 text-sm text-text-primary
                         placeholder:text-text-muted
                         focus:outline-none focus:border-blue-500/50
                         transition-all duration-200"
            />
          </div>
          <div className="flex-[2] space-y-1.5">
            <p className="text-[13px] text-text-secondary">Duration (min)</p>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="45"
              min={1}
              max={600}
              className="w-full bg-surface border border-border rounded-xl
                         px-3 py-2.5 text-sm text-text-primary
                         placeholder:text-text-muted
                         focus:outline-none focus:border-blue-500/50
                         transition-all duration-200"
            />
          </div>
        </div>

        {/* Exercises */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[13px] text-text-secondary">Exercises</p>
            {exerciseHistory.length > 0 && (
              <p className="text-xs text-text-muted">{exerciseHistory.length} saved</p>
            )}
          </div>

          {/* Column headers */}
          <div className="flex items-center gap-2 px-1">
            <p className="flex-1 text-[11px] text-text-muted">Exercise</p>
            <p className="w-12 text-center text-[11px] text-text-muted">Sets</p>
            <p className="w-12 text-center text-[11px] text-text-muted">Reps</p>
            <div className="w-8" />
          </div>

          {/* Exercise rows */}
          <AnimatePresence initial={false}>
            {rows.map((row) => (
              <motion.div
                key={row.id}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-2"
              >
                <ExerciseAutocomplete
                  value={row.name}
                  onChange={(v) => updateRow(row.id, "name", v)}
                  history={exerciseHistory}
                  placeholder="Exercise name"
                />
                <input
                  type="number"
                  value={row.sets}
                  onChange={(e) => updateRow(row.id, "sets", e.target.value)}
                  placeholder="3"
                  min={1}
                  className="w-12 bg-surface border border-border rounded-xl
                             px-2 py-2.5 text-sm text-center text-text-primary
                             placeholder:text-text-muted
                             focus:outline-none focus:border-blue-500/50
                             transition-all duration-200"
                />
                <input
                  type="number"
                  value={row.reps}
                  onChange={(e) => updateRow(row.id, "reps", e.target.value)}
                  placeholder="10"
                  min={1}
                  className="w-12 bg-surface border border-border rounded-xl
                             px-2 py-2.5 text-sm text-center text-text-primary
                             placeholder:text-text-muted
                             focus:outline-none focus:border-blue-500/50
                             transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => removeRow(row.id)}
                  className={cn(
                    "w-8 h-8 flex items-center justify-center rounded-lg transition-colors",
                    rows.length === 1
                      ? "opacity-20 cursor-not-allowed"
                      : "text-text-muted hover:text-red-400"
                  )}
                  disabled={rows.length === 1}
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Add exercise */}
          <button
            type="button"
            onClick={addRow}
            className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium
                       hover:text-blue-300 transition-colors py-1"
          >
            <Plus className="w-4 h-4" />
            Add exercise
          </button>
        </div>

        {/* Calories burned card */}
        <div className="flex items-center gap-3 bg-surface-elevated border border-border rounded-xl p-3.5">
          <Flame className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-text-secondary mb-1">Calories burned</p>
            <input
              type="number"
              value={calories}
              onChange={(e) => setCalories(e.target.value)}
              placeholder="450"
              min={0}
              className="w-full bg-transparent text-[22px] font-bold text-text-primary
                         placeholder:text-text-muted focus:outline-none"
            />
          </div>
          <p className="text-[11px] text-text-muted text-right leading-tight shrink-0">
            from<br />your app
          </p>
        </div>

        {/* Success banner */}
        <AnimatePresence>
          {success && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 bg-emerald-500/10 rounded-xl px-3 py-2.5"
            >
              <Check className="w-4 h-4 text-emerald-400 shrink-0" strokeWidth={2.5} />
              <p className="text-sm text-emerald-400">{success}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Log button */}
        <button
          type="submit"
          disabled={loading || rows.every((r) => !r.name.trim())}
          className="w-full py-3 rounded-xl bg-blue-500 text-white text-sm font-semibold
                     hover:bg-blue-600 transition-colors disabled:opacity-40
                     flex items-center justify-center gap-2"
        >
          {loading
            ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <Dumbbell className="w-4 h-4" />}
          {loading ? "Logging…" : "Log Workout"}
        </button>
      </form>

      {/* Recent workouts */}
      <div>
        <p className="text-[15px] font-semibold mb-2.5">Recent Workouts</p>
        {recentWorkouts.length === 0 ? (
          <p className="text-center text-text-muted py-8 text-sm">No workouts yet.</p>
        ) : (
          <div className="space-y-2">
            {recentWorkouts.map((log, i) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="card-surface flex items-center gap-3 px-4 py-3.5"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0">
                  <Dumbbell className="w-5 h-5 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{log.title}</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {WORKOUT_TYPES.find((t) => t.value === log.workout_type)?.label ?? log.workout_type}
                    {" · "}{log.duration_minutes} min
                    {log.exercises.length > 0 && ` · ${log.exercises.length} exercise${log.exercises.length !== 1 ? "s" : ""}`}
                  </p>
                </div>
                {log.calories_burned != null && (
                  <p className="text-sm font-semibold text-amber-400 tabular-nums shrink-0">
                    {Math.round(log.calories_burned)} kcal
                  </p>
                )}
              </motion.div>
            ))}
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

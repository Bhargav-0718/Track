"use client";

import {
  useState, useRef, useId,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, X, ChevronDown, ChevronUp,
  Trash2, Dumbbell, Flame, Check, Plus, History,
  Bike, BedDouble, Smartphone, Bookmark, BookmarkCheck,
} from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { format } from "date-fns";
import { useSearchParams, useRouter } from "next/navigation";

import { foodApi } from "@/lib/api/food";
import { foodItemsApi } from "@/lib/api/food_items";
import { ApiError } from "@/lib/api/client";
import { workoutApi } from "@/lib/api/workout";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import {
  formatCalories, formatGrams, formatMealType, formatDate,
  getSourceInfo, todayISO, MEAL_LABELS, cn
} from "@/lib/utils/format";
import type {
  FoodLog, MealType, WorkoutLog, WorkoutType,
  CardioActivityInput, StrengthExerciseInput, WorkoutSection, UserFoodItem,
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

// Derives a portion label like "plate" from a portion description like "1 plate poha"
// (used to pre-fill the "save to my food list" form).
function guessUnitLabel(portionDescription: string | null, foodName: string): string {
  const fn = foodName.trim().toLowerCase();
  if (!portionDescription) return fn;
  let s = portionDescription.trim().toLowerCase().replace(fn, "").trim();
  s = s.replace(/^\d+(\.\d+)?\s*/, "").trim();
  return s || fn;
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
  const [showSave, setShowSave] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(log.estimation_source === "user_db");
  const [unitLabel, setUnitLabel] = useState(() => guessUnitLabel(log.portion_description, log.food_name));
  const [calories, setCalories] = useState(() => String(Math.round(log.calories)));

  async function handleDelete() {
    setDeleting(true);
    try {
      await foodApi.deleteLog(log.id);
      onDelete(log.id);
    } catch {
      setDeleting(false);
    }
  }

  async function handleSaveToFoodList() {
    setSaving(true);
    try {
      await foodItemsApi.upsert({
        food_name: log.food_name.toLowerCase(),
        unit_label: (unitLabel.trim() || log.food_name).toLowerCase(),
        portion_description: log.portion_description || `1 ${log.food_name}`,
        calories: parseFloat(calories) || log.calories,
        portion_grams: log.portion_grams ?? undefined,
        protein_g: log.protein_g ?? undefined,
        carbs_g: log.carbs_g ?? undefined,
        fat_g: log.fat_g ?? undefined,
        fiber_g: log.fiber_g ?? undefined,
      });
      setSaved(true);
      setShowSave(false);
    } catch {
      // best-effort — leave the form open so the user can retry
    } finally {
      setSaving(false);
    }
  }

  const qty = log.quantity ?? 1;
  const perUnit = log.calories_per_unit;

  return (
    <div className="py-2 border-b border-border-subtle last:border-0">
      <div className="flex items-center gap-2">
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
          onClick={() => !saved && setShowSave((v) => !v)}
          disabled={saved}
          title={saved ? "Saved to your food list" : "Save this portion to your food list"}
          className={cn(
            "p-1 transition-colors disabled:opacity-100 shrink-0",
            saved ? "text-emerald-400" : "text-text-muted hover:text-emerald-400"
          )}
        >
          {saved ? <BookmarkCheck className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
        </button>
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

      <AnimatePresence>
        {showSave && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-2 mt-2 pb-1">
              <input
                value={unitLabel}
                onChange={(e) => setUnitLabel(e.target.value)}
                placeholder="portion (e.g. plate)"
                className="flex-1 min-w-0 bg-surface border border-border rounded-lg px-2.5 py-1.5
                           text-xs text-text-primary placeholder:text-text-muted
                           focus:outline-none focus:border-emerald-500/50"
              />
              <input
                type="number"
                value={calories}
                onChange={(e) => setCalories(e.target.value)}
                className="w-20 bg-surface border border-border rounded-lg px-2.5 py-1.5
                           text-xs text-text-primary tabular-nums
                           focus:outline-none focus:border-emerald-500/50"
              />
              <span className="text-[11px] text-text-muted shrink-0">kcal</span>
              <button
                onClick={handleSaveToFoodList}
                disabled={saving}
                className="px-2.5 py-1.5 rounded-lg bg-emerald-500 text-white text-xs font-semibold
                           hover:bg-emerald-600 transition-colors disabled:opacity-40 shrink-0"
              >
                {saving ? "…" : "Save"}
              </button>
            </div>
            <p className="text-[10px] text-text-muted">
              Next time you log "{guessUnitLabel(log.portion_description, log.food_name)} {log.food_name}",
              this exact value will be used — no AI guessing.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
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
  const [manualCalories, setManualCalories] = useState("");
  const [mealType, setMealType] = useState<MealType>("lunch");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Set when the backend can't guess a portion and has no saved data to fall
  // back on — we ask the user for the portion + calories instead of guessing.
  const [needsInfo, setNeedsInfo] = useState<{ foodName: string } | null>(null);
  const [infoPortion, setInfoPortion] = useState("");
  const [infoCalories, setInfoCalories] = useState("");
  const [infoSaving, setInfoSaving] = useState(false);

  const [suggestions, setSuggestions] = useState<UserFoodItem[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleQueryChange(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = value.trim();
    if (trimmed.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await foodItemsApi.search(trimmed);
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
  }

  async function handleSelectSuggestion(item: UserFoodItem) {
    if (loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      await foodApi.createLog({
        food_name: item.display_name,
        calories: item.calories,
        meal_type: mealType,
        portion_description: item.portion_description,
        portion_grams: item.portion_grams ?? undefined,
        protein_g: item.protein_g ?? undefined,
        carbs_g: item.carbs_g ?? undefined,
        fat_g: item.fat_g ?? undefined,
        fiber_g: item.fiber_g ?? undefined,
        from_user_food_item: true,
      });
      setResult(`${item.portion_description} — ${Math.round(item.calories)} kcal logged!`);
      setQuery("");
      setSuggestions([]);
      setShowSuggestions(false);
      onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log food");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setNeedsInfo(null);
    setShowSuggestions(false);
    try {
      const manualKcal = parseFloat(manualCalories);
      if (manualCalories.trim() && !isNaN(manualKcal) && manualKcal > 0) {
        // User provided their own calorie count — log it directly, no AI call.
        const foodName = query.trim();
        const logs = await foodApi.createLog({
          food_name: foodName,
          calories: manualKcal,
          portion_description: foodName,
          meal_type: mealType,
        });
        setResult(`${logs[0].food_name} — ${Math.round(manualKcal)} kcal logged!`);

        // Save to personal food list so next time it's an autocomplete suggestion.
        try {
          await foodItemsApi.upsert({
            food_name: foodName.toLowerCase(),
            unit_label: foodName.toLowerCase(),
            portion_description: foodName,
            calories: manualKcal,
          });
        } catch {
          // best-effort
        }
        setQuery("");
        setManualCalories("");
      } else {
        const logs = await foodApi.createLog({ raw_input: query.trim(), meal_type: mealType });
        const totalKcal = logs.reduce((s, l) => s + l.calories, 0);
        const label = logs.length === 1
          ? logs[0].food_name
          : logs.map((l) => l.food_name).join(" + ");
        setResult(`${label} — ${Math.round(totalKcal)} kcal logged!`);
        setQuery("");
        setManualCalories("");
      }
      onLogged();
    } catch (err) {
      const code = (err as ApiError)?.details?.details as { code?: string; food_name?: string } | undefined;
      if (err instanceof ApiError && code?.code === "needs_portion_input" && code.food_name) {
        setNeedsInfo({ foodName: code.food_name });
        setInfoPortion("");
        setInfoCalories("");
      } else {
        setError(err instanceof Error ? err.message : "Failed to log food");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitClarification(e: React.FormEvent) {
    e.preventDefault();
    if (!needsInfo) return;
    const kcal = parseFloat(infoCalories);
    if (!infoPortion.trim() || isNaN(kcal) || kcal <= 0) return;
    setInfoSaving(true);
    setError(null);
    try {
      const foodName = needsInfo.foodName;
      const portionDescription = infoPortion.trim();
      const logs = await foodApi.createLog({
        food_name: foodName,
        calories: kcal,
        portion_description: portionDescription,
        meal_type: mealType,
      });
      setResult(`${logs[0].food_name} — ${Math.round(kcal)} kcal logged!`);

      // Remember this portion so next time it's used automatically.
      try {
        await foodItemsApi.upsert({
          food_name: foodName.toLowerCase(),
          unit_label: guessUnitLabel(portionDescription, foodName),
          portion_description: portionDescription,
          calories: kcal,
        });
      } catch {
        // best-effort
      }

      setQuery("");
      setManualCalories("");
      setNeedsInfo(null);
      onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log food");
    } finally {
      setInfoSaving(false);
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
          <div className="relative">
            <textarea
              ref={inputRef}
              rows={3}
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder='e.g. "2 rotis with dal and sabzi" or "protein shake 30g"'
              className="w-full bg-surface border border-border rounded-xl
                         px-4 py-3 text-sm text-text-primary resize-none
                         placeholder:text-text-muted
                         focus:outline-none focus:border-emerald-500/50
                         transition-all duration-200"
              disabled={loading}
            />

            {/* Saved-portion autocomplete */}
            <AnimatePresence>
              {showSuggestions && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="absolute z-10 left-0 right-0 top-full mt-1.5 card-surface
                             border border-border overflow-hidden"
                >
                  <p className="text-[10px] font-medium text-text-muted uppercase tracking-wide px-3 pt-2">
                    From your food list
                  </p>
                  <div className="max-h-56 overflow-y-auto py-1">
                    {suggestions.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onMouseDown={() => handleSelectSuggestion(item)}
                        className="w-full flex items-center justify-between gap-2 px-3 py-2
                                   hover:bg-surface-elevated transition-colors text-left"
                      >
                        <span className="text-sm text-text-primary capitalize truncate">
                          {item.portion_description}
                        </span>
                        <span className="text-xs font-semibold tabular-nums text-text-secondary shrink-0">
                          {Math.round(item.calories)} kcal
                        </span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Optional manual calorie entry — skips the AI call when provided */}
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={manualCalories}
              onChange={(e) => setManualCalories(e.target.value)}
              placeholder="kcal (optional)"
              min={0}
              className="w-32 bg-surface border border-border rounded-xl px-3 py-2
                         text-sm text-text-primary tabular-nums placeholder:text-text-muted
                         focus:outline-none focus:border-emerald-500/50 transition-all"
              disabled={loading}
            />
            <p className="text-[11px] text-text-muted flex-1">
              Know the calories? Enter them to skip AI and save to your food list.
            </p>
          </div>

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

          {/* Needs clarification — no saved portion or known piece weight to fall back on */}
          <AnimatePresence>
            {needsInfo && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 space-y-2"
              >
                <p className="text-sm text-amber-300 capitalize">
                  How much {needsInfo.foodName} did you have?
                </p>
                <div className="flex items-center gap-2">
                  <input
                    value={infoPortion}
                    onChange={(e) => setInfoPortion(e.target.value)}
                    placeholder="portion (e.g. 1 bowl, 2 pieces)"
                    className="flex-1 min-w-0 bg-surface border border-border rounded-lg px-2.5 py-1.5
                               text-sm text-text-primary placeholder:text-text-muted
                               focus:outline-none focus:border-emerald-500/50"
                  />
                  <input
                    type="number"
                    value={infoCalories}
                    onChange={(e) => setInfoCalories(e.target.value)}
                    placeholder="kcal"
                    min={0}
                    className="w-20 bg-surface border border-border rounded-lg px-2.5 py-1.5
                               text-sm text-text-primary tabular-nums placeholder:text-text-muted
                               focus:outline-none focus:border-emerald-500/50"
                  />
                  <button
                    type="button"
                    onClick={handleSubmitClarification}
                    disabled={infoSaving || !infoPortion.trim() || !infoCalories.trim()}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500 text-white text-sm font-semibold
                               hover:bg-emerald-600 transition-colors disabled:opacity-40 shrink-0"
                  >
                    {infoSaving ? "…" : "Log"}
                  </button>
                </div>
                <p className="text-[11px] text-amber-300/70">
                  We'll remember this for next time.
                </p>
              </motion.div>
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
            {loading
              ? (manualCalories.trim() ? "Logging…" : "Estimating…")
              : (manualCalories.trim() ? "Log" : "Estimate & Log")}
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

interface SkipSet { id: string; jumps: string; weight: string; }
function newSkipSet(id: string): SkipSet { return { id, jumps: "", weight: "" }; }

function CardioSection({ onLogged }: { onLogged: () => void }) {
  const [rows, setRows] = useState<CardioRow[]>([newCardioRow("0")]);
  const [nextId, setNextId] = useState(1);
  const [isRest, setIsRest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showSkipping, setShowSkipping] = useState(false);
  const [skipSets, setSkipSets] = useState<SkipSet[]>([newSkipSet("0")]);
  const [nextSkipId, setNextSkipId] = useState(1);
  const [skipMinutes, setSkipMinutes] = useState("");

  function addRow() { setRows((r) => [...r, newCardioRow(String(nextId))]); setNextId((n) => n + 1); }
  function removeRow(id: string) { if (rows.length > 1) setRows((r) => r.filter((row) => row.id !== id)); }
  function update(id: string, field: keyof Omit<CardioRow, "id">, val: string) {
    setRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }

  function addSkipSet() { setSkipSets((s) => [...s, newSkipSet(String(nextSkipId))]); setNextSkipId((n) => n + 1); }
  function removeSkipSet(id: string) { if (skipSets.length > 1) setSkipSets((s) => s.filter((set) => set.id !== id)); }
  function updateSkip(id: string, field: keyof Omit<SkipSet, "id">, val: string) {
    setSkipSets((s) => s.map((set) => set.id === id ? { ...set, [field]: val } : set));
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
      const validSkipSets = skipSets.filter((s) => s.jumps.trim());
      const hasSkipping = validSkipSets.length > 0 && skipMinutes.trim();
      if (!valid.length && !hasSkipping) return;
      const activities: CardioActivityInput[] = valid.map((r) => ({
        activity_description: r.activity.trim(),
        duration_minutes: parseFloat(r.duration) || 0,
        ...(r.calories.trim() ? { calories_burned: parseFloat(r.calories) } : {}),
      }));
      if (hasSkipping) {
        const setsDesc = validSkipSets.map((s, i) => {
          const w = parseFloat(s.weight);
          return `Set ${i + 1}: ${s.jumps} jumps` + (w > 0 ? ` while holding ${w}kg dumbbells in each hand` : "");
        }).join("; ");
        activities.push({
          activity_description: `Skipping/jump-rope motion (no rope) — ${setsDesc}`,
          duration_minutes: parseFloat(skipMinutes) || 0,
        });
      }
      const logs = await workoutApi.createSectionedLog({ section: "cardio", cardio_activities: activities });
      const totalKcal = logs.reduce((s, l) => s + (l.calories_burned ?? 0), 0);
      setSuccess(`${logs.length} activit${logs.length !== 1 ? "ies" : "y"} logged · ${Math.round(totalKcal)} kcal`);
      setRows([newCardioRow(String(nextId))]);
      setNextId((n) => n + 1);
      setSkipSets([newSkipSet("0")]);
      setNextSkipId(1);
      setSkipMinutes("");
      setShowSkipping(false);
      onLogged();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? "Failed to log cardio — check your connection");
    } finally {
      setLoading(false);
    }
  }

  const hasValidSkipSets = skipSets.some((s) => s.jumps.trim()) && skipMinutes.trim().length > 0;
  const hasAiEstimate = !isRest && (
    rows.some((r) => r.activity.trim() && r.duration.trim() && !r.calories.trim()) || hasValidSkipSets
  );

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

          {/* Skipping / jump-rope sets */}
          <div className="pt-1">
            <button type="button" onClick={() => setShowSkipping((v) => !v)}
              className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium hover:text-blue-300 transition-colors py-1">
              {showSkipping ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              Skipping (jump-rope) sets
            </button>

            <AnimatePresence initial={false}>
              {showSkipping && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                  className="space-y-2 overflow-hidden pt-1">
                  <div className="flex gap-2 px-1">
                    <p className="w-10 text-[11px] text-text-muted">Set</p>
                    <p className="flex-1 text-center text-[11px] text-text-muted">Jumps</p>
                    <p className="flex-1 text-center text-[11px] text-text-muted">Dumbbell kg/hand</p>
                    <div className="w-7" />
                  </div>
                  {skipSets.map((s, i) => (
                    <div key={s.id} className="flex gap-2 items-center">
                      <p className="w-10 text-sm text-text-muted text-center">{i + 1}</p>
                      <FieldInput value={s.jumps} onChange={(v) => updateSkip(s.id, "jumps", v)}
                        placeholder="100" type="number" className="flex-1 text-center" />
                      <FieldInput value={s.weight} onChange={(v) => updateSkip(s.id, "weight", v)}
                        placeholder="0" type="number" className="flex-1 text-center" />
                      <button type="button" onClick={() => removeSkipSet(s.id)}
                        className={cn("w-7 h-7 flex items-center justify-center rounded-lg transition-colors",
                          skipSets.length === 1 ? "opacity-20 cursor-not-allowed" : "text-text-muted hover:text-red-400"
                        )} disabled={skipSets.length === 1}>
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                  <button type="button" onClick={addSkipSet}
                    className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium hover:text-blue-300 transition-colors py-1">
                    <Plus className="w-4 h-4" /> Add set
                  </button>
                  <div className="flex items-center gap-2 pt-1">
                    <p className="text-[13px] text-text-secondary flex-1">Total time skipping</p>
                    <FieldInput value={skipMinutes} onChange={setSkipMinutes}
                      placeholder="10" type="number" className="w-16 text-center" />
                    <span className="text-[13px] text-text-muted">min</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
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
        disabled={loading || (!isRest
          && rows.every((r) => !r.activity.trim() || !r.duration.trim())
          && !hasValidSkipSets)}
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

interface StrSetRow { id: string; weight: string; reps: string; }
function newSetRow(id: string): StrSetRow { return { id, weight: "", reps: "" }; }

interface StrExerciseRow { id: string; name: string; sets: StrSetRow[]; }
function newExerciseRow(id: string): StrExerciseRow { return { id, name: "", sets: [newSetRow(`${id}-0`)] }; }

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
  const idCounter = useRef(1);
  function genId() { return String(idCounter.current++); }

  const [exercises, setExercises] = useState<StrExerciseRow[]>([newExerciseRow("0")]);
  const [isRest, setIsRest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const exerciseHistory: string[] = Array.from(
    new Set(recentWorkouts
      .filter((w) => w.workout_section === "strength")
      .flatMap((w) => (w.exercises ?? []).map((e: any) => e.name as string).filter(Boolean))
    )
  ).sort();

  function addExercise() { setExercises((ex) => [...ex, newExerciseRow(genId())]); }
  function removeExercise(id: string) { if (exercises.length > 1) setExercises((ex) => ex.filter((e) => e.id !== id)); }
  function updateExerciseName(id: string, name: string) {
    setExercises((ex) => ex.map((e) => e.id === id ? { ...e, name } : e));
  }
  function addSet(exId: string) {
    setExercises((ex) => ex.map((e) => e.id === exId ? { ...e, sets: [...e.sets, newSetRow(genId())] } : e));
  }
  function removeSet(exId: string, setId: string) {
    setExercises((ex) => ex.map((e) => e.id === exId
      ? (e.sets.length > 1 ? { ...e, sets: e.sets.filter((s) => s.id !== setId) } : e)
      : e));
  }
  function updateSet(exId: string, setId: string, field: keyof Omit<StrSetRow, "id">, val: string) {
    setExercises((ex) => ex.map((e) => e.id === exId
      ? { ...e, sets: e.sets.map((s) => s.id === setId ? { ...s, [field]: val } : s) }
      : e));
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
      const payload: StrengthExerciseInput[] = [];
      for (const ex of exercises) {
        if (!ex.name.trim()) continue;
        const validSets = ex.sets.filter((s) => s.reps.trim());
        if (!validSets.length) continue;
        const numSets = validSets.length;
        const totalReps = validSets.reduce((s, set) => s + (parseFloat(set.reps) || 0), 0);
        const avgReps = Math.max(1, Math.round(totalReps / numSets));
        const totalVolume = validSets.reduce((s, set) => s + (parseFloat(set.reps) || 0) * (parseFloat(set.weight) || 0), 0);
        const weight_kg = totalVolume > 0 ? totalVolume / (numSets * avgReps) : 0;
        const set_details = validSets.map((set) => ({
          reps: parseInt(set.reps) || 0,
          weight_kg: parseFloat(set.weight) || 0,
        }));
        payload.push({ name: ex.name.trim(), sets: numSets, reps: avgReps, weight_kg, set_details });
      }
      if (!payload.length) return;
      const logs = await workoutApi.createSectionedLog({ section: "strength", strength_exercises: payload });
      const totalKcal = logs.reduce((s, l) => s + (l.calories_burned ?? 0), 0);
      setSuccess(`${logs.length} exercise${logs.length !== 1 ? "s" : ""} logged · ${Math.round(totalKcal)} kcal`);
      setExercises([newExerciseRow(genId())]);
      onLogged();
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }

  const hasValidExercise = exercises.some((e) => e.name.trim() && e.sets.some((s) => s.reps.trim()));

  return (
    <form onSubmit={handleLog} className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">
          AI estimates calories from your sets × reps × weight.
        </p>
        <RestDayToggle checked={isRest} onChange={setIsRest} />
      </div>

      {!isRest && (
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {exercises.map((ex) => (
              <motion.div key={ex.id}
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                className="card-surface p-3 space-y-2 overflow-hidden">
                <div className="flex items-center gap-2">
                  <ExerciseAutocomplete
                    value={ex.name} onChange={(v) => updateExerciseName(ex.id, v)}
                    history={exerciseHistory} placeholder="Bench Press, Squat…" />
                  <button type="button" onClick={() => removeExercise(ex.id)}
                    className={cn("w-7 h-7 flex items-center justify-center rounded-lg transition-colors",
                      exercises.length === 1 ? "opacity-20 cursor-not-allowed" : "text-text-muted hover:text-red-400"
                    )} disabled={exercises.length === 1}>
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Column headers */}
                <div className="flex gap-2 px-1">
                  <p className="w-10 text-[11px] text-text-muted">Set</p>
                  <p className="flex-1 text-center text-[11px] text-text-muted">kg</p>
                  <p className="flex-1 text-center text-[11px] text-text-muted">Reps</p>
                  <div className="w-7" />
                </div>

                <AnimatePresence initial={false}>
                  {ex.sets.map((s, i) => (
                    <motion.div key={s.id}
                      initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                      className="flex gap-2 items-center">
                      <p className="w-10 text-sm text-text-muted text-center">{i + 1}</p>
                      <FieldInput value={s.weight} onChange={(v) => updateSet(ex.id, s.id, "weight", v)}
                        placeholder="0" type="number" className="flex-1 text-center" />
                      <FieldInput value={s.reps} onChange={(v) => updateSet(ex.id, s.id, "reps", v)}
                        placeholder="10" type="number" className="flex-1 text-center" />
                      <button type="button" onClick={() => removeSet(ex.id, s.id)}
                        className={cn("w-7 h-7 flex items-center justify-center rounded-lg transition-colors",
                          ex.sets.length === 1 ? "opacity-20 cursor-not-allowed" : "text-text-muted hover:text-red-400"
                        )} disabled={ex.sets.length === 1}>
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>

                <button type="button" onClick={() => addSet(ex.id)}
                  className="flex items-center gap-1.5 text-blue-400 text-[13px] font-medium hover:text-blue-300 transition-colors py-1">
                  <Plus className="w-4 h-4" /> Add a set
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          <button type="button" onClick={addExercise}
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
        disabled={loading || (!isRest && !hasValidExercise)}
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

// ── Date grouping helper ────────────────────────────────────────────────────────

interface WorkoutDayGroup {
  date: string;
  logs: WorkoutLog[];
  totalCalories: number;
}

function groupWorkoutsByDate(logs: WorkoutLog[]): WorkoutDayGroup[] {
  const map = new Map<string, WorkoutLog[]>();
  for (const log of logs) {
    const dateKey = log.logged_at.slice(0, 10); // YYYY-MM-DD
    if (!map.has(dateKey)) map.set(dateKey, []);
    map.get(dateKey)!.push(log);
  }
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, dayLogs]) => ({
      date,
      logs: dayLogs,
      totalCalories: dayLogs
        .filter((l) => !l.is_rest_day)
        .reduce((s, l) => s + (l.calories_burned ?? 0), 0),
    }));
}

// ── WorkoutTab orchestrator ────────────────────────────────────────────────────

function WorkoutTab({ onLogged, recentWorkouts, mutateRecent }: {
  onLogged: () => void;
  recentWorkouts: WorkoutLog[];
  mutateRecent: () => void;
}) {
  const [activeSection, setActiveSection] = useState<WorkoutSection>("app_workout");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
        <div className="flex items-center justify-between mb-2.5">
          <p className="text-[15px] font-semibold">Recent Workouts</p>
          {recentWorkouts.length > 0 && (
            <div className="flex items-center gap-1.5">
              <Flame className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-semibold text-amber-400 tabular-nums">
                {Math.round(
                  recentWorkouts
                    .filter((l) => !l.is_rest_day)
                    .reduce((s, l) => s + (l.calories_burned ?? 0), 0)
                )} kcal total
              </span>
            </div>
          )}
        </div>
        {recentWorkouts.length === 0 ? (
          <p className="text-center text-text-muted py-8 text-sm">No workouts yet.</p>
        ) : (
          <div className="space-y-5">
            {groupWorkoutsByDate(recentWorkouts).map((group) => (
              <div key={group.date}>
                <div className="flex items-center justify-between mb-2 px-1">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    {formatDate(group.date)}
                  </p>
                  {group.totalCalories > 0 && (
                    <p className="text-xs font-medium text-amber-400 tabular-nums">
                      {Math.round(group.totalCalories)} kcal
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  {group.logs.map((log, i) => {
                    const sectionIcon =
                      log.workout_section === "cardio" ? <Bike className="w-5 h-5 text-blue-400" />
                      : log.workout_section === "strength" ? <Dumbbell className="w-5 h-5 text-blue-400" />
                      : log.is_rest_day ? <BedDouble className="w-5 h-5 text-slate-400" />
                      : <Smartphone className="w-5 h-5 text-blue-400" />;
                    const setDetails = log.workout_section === "strength"
                      ? (log.exercises?.[0]?.set_details as { reps: number; weight_kg: number }[] | undefined)
                      : undefined;
                    const hasSetDetails = !!setDetails && setDetails.length > 0;
                    const isExpanded = expandedId === log.id;
                    return (
                      <motion.div key={log.id}
                        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="card-surface overflow-hidden">
                        <div
                          onClick={() => hasSetDetails && setExpandedId(isExpanded ? null : log.id)}
                          className={cn("flex items-center gap-3 px-4 py-3.5", hasSetDetails && "cursor-pointer")}
                        >
                          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0">
                            {sectionIcon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-text-primary truncate">{log.title}</p>
                            <p className="text-xs text-text-muted mt-0.5">
                              {log.is_rest_day ? "Rest day"
                                : log.workout_section === "strength" ? "Strength"
                                : log.workout_section === "cardio"
                                  ? `Cardio${log.duration_minutes > 0 ? ` · ${log.duration_minutes} min` : ""}`
                                  : `App${log.duration_minutes > 0 ? ` · ${log.duration_minutes} min` : ""}`
                              }
                              {hasSetDetails && ` · ${setDetails!.length} set${setDetails!.length !== 1 ? "s" : ""}`}
                              {(log.exercises?.length ?? 0) > 0 && !log.is_rest_day && !hasSetDetails && log.workout_section !== "strength" && ` · ${log.exercises!.length} item${log.exercises!.length !== 1 ? "s" : ""}`}
                            </p>
                          </div>
                          {log.calories_burned != null && log.calories_burned > 0 && (
                            <p className="text-sm font-semibold text-amber-400 tabular-nums shrink-0">
                              {Math.round(log.calories_burned)} kcal
                            </p>
                          )}
                          {hasSetDetails && (
                            isExpanded
                              ? <ChevronUp className="w-4 h-4 text-text-muted shrink-0" />
                              : <ChevronDown className="w-4 h-4 text-text-muted shrink-0" />
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteWorkout(log.id); }}
                            disabled={deletingId === log.id}
                            className="ml-1 p-1.5 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-40 shrink-0"
                          >
                            {deletingId === log.id
                              ? <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                              : <Trash2 className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                        <AnimatePresence initial={false}>
                          {hasSetDetails && isExpanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }}
                              className="overflow-hidden border-t border-border"
                            >
                              <div className="px-4 py-2.5 space-y-1.5">
                                {setDetails!.map((s, idx) => (
                                  <div key={idx} className="flex items-center justify-between text-xs text-text-secondary">
                                    <span className="text-text-muted">Set {idx + 1}</span>
                                    <span className="tabular-nums">
                                      {s.weight_kg > 0 ? `${s.weight_kg} kg × ` : ""}{s.reps} reps
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
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

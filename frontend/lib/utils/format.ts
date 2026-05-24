import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from "date-fns";

// ── Numbers ───────────────────────────────────────────────────────────────────

export function formatCalories(cal: number): string {
  return Math.round(cal).toLocaleString();
}

export function formatGrams(g: number | null | undefined): string {
  if (g == null) return "—";
  return `${Math.round(g)}g`;
}

export function formatKg(kg: number | null | undefined): string {
  if (kg == null) return "—";
  return `${kg.toFixed(1)} kg`;
}

export function formatPct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}`;
}

// ── Dates ─────────────────────────────────────────────────────────────────────

export function formatDate(dateStr: string): string {
  const d = parseISO(dateStr);
  if (isToday(d)) return "Today";
  if (isYesterday(d)) return "Yesterday";
  return format(d, "MMM d");
}

export function formatDateFull(dateStr: string): string {
  return format(parseISO(dateStr), "EEEE, MMMM d");
}

export function formatDateShort(dateStr: string): string {
  return format(parseISO(dateStr), "MMM d, yyyy");
}

export function formatRelative(dateStr: string): string {
  return formatDistanceToNow(parseISO(dateStr), { addSuffix: true });
}

export function todayISO(): string {
  return format(new Date(), "yyyy-MM-dd");
}

// ── Meal types ────────────────────────────────────────────────────────────────

export const MEAL_LABELS: Record<string, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
  pre_workout: "Pre-Workout",
  post_workout: "Post-Workout",
};

export function formatMealType(type: string): string {
  return MEAL_LABELS[type] ?? type;
}

// ── Estimation source ─────────────────────────────────────────────────────────

export const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  memory: { label: "Memory", color: "text-emerald-400" },
  dataset: { label: "Database", color: "text-blue-400" },
  llm: { label: "AI Estimate", color: "text-indigo-400" },
  manual: { label: "Manual", color: "text-zinc-400" },
  photo: { label: "Photo AI", color: "text-purple-400" },
  health_connect: { label: "Health Connect", color: "text-cyan-400" },
};

export function getSourceInfo(source: string) {
  return SOURCE_LABELS[source] ?? { label: source, color: "text-zinc-400" };
}

// ── Confidence level ──────────────────────────────────────────────────────────

export const CONFIDENCE_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; dots: number }
> = {
  confirmed: {
    label: "Confirmed",
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    dots: 5,
  },
  estimated: {
    label: "Estimated",
    bg: "bg-blue-500/15",
    text: "text-blue-400",
    dots: 3,
  },
  uncertain: {
    label: "Uncertain",
    bg: "bg-zinc-700/50",
    text: "text-zinc-400",
    dots: 1,
  },
};

export function getConfidenceConfig(level: string) {
  return CONFIDENCE_CONFIG[level] ?? CONFIDENCE_CONFIG.uncertain;
}

// ── Workout ───────────────────────────────────────────────────────────────────

export const WORKOUT_ICONS: Record<string, string> = {
  strength: "🏋️",
  cardio: "🏃",
  hiit: "⚡",
  yoga: "🧘",
  sports: "⚽",
  other: "💪",
};

// ── Goal ──────────────────────────────────────────────────────────────────────

export const GOAL_LABELS: Record<string, string> = {
  lose_weight: "Lose Weight",
  maintain: "Maintain",
  gain_muscle: "Gain Muscle",
  improve_fitness: "Improve Fitness",
};

// ── Greeting ──────────────────────────────────────────────────────────────────

export function getGreeting(name?: string): { text: string; emoji: string } {
  const hour = new Date().getHours();
  if (hour < 5) return { text: `Good night${name ? `, ${name}` : ""}`, emoji: "🌙" };
  if (hour < 12) return { text: `Good morning${name ? `, ${name}` : ""}`, emoji: "☀️" };
  if (hour < 17) return { text: `Good afternoon${name ? `, ${name}` : ""}`, emoji: "🌤️" };
  if (hour < 21) return { text: `Good evening${name ? `, ${name}` : ""}`, emoji: "🌆" };
  return { text: `Good night${name ? `, ${name}` : ""}`, emoji: "🌙" };
}

// ── Macro colors ──────────────────────────────────────────────────────────────

export const MACRO_COLORS = {
  calories: { bar: "#10b981", bg: "bg-emerald-500" },
  protein: { bar: "#3b82f6", bg: "bg-blue-500" },
  carbs: { bar: "#f59e0b", bg: "bg-amber-500" },
  fat: { bar: "#8b5cf6", bg: "bg-violet-500" },
  fiber: { bar: "#6b7280", bg: "bg-zinc-500" },
};

// ── cn utility ────────────────────────────────────────────────────────────────
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

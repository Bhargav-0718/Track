"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Target,
  Activity,
  Brain,
  Bell,
  LogOut,
  ChevronRight,
  Check,
  Loader2,
  Pencil,
  X,
  Scale,
  Ruler,
  Calendar,
  Flame,
  Beef,
  Wheat,
  Droplets,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";

import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth";
import { formatKg, formatCalories, GOAL_LABELS, cn } from "@/lib/utils/format";
import type { ReportStyle } from "@/lib/types";

// ── Constants ──────────────────────────────────────────────────────────────────

const GOAL_OPTIONS: { value: string; label: string; emoji: string; description: string }[] = [
  { value: "lose_weight", label: "Lose Weight", emoji: "⬇️", description: "Caloric deficit with fat loss focus" },
  { value: "maintain", label: "Maintain", emoji: "⚖️", description: "Balance calories in and out" },
  { value: "gain_muscle", label: "Gain Muscle", emoji: "💪", description: "Surplus with protein priority" },
  { value: "improve_fitness", label: "Improve Fitness", emoji: "🏃", description: "Performance and endurance" },
];

const ACTIVITY_OPTIONS: { value: string; label: string; description: string }[] = [
  { value: "sedentary", label: "Sedentary", description: "Little or no exercise" },
  { value: "light", label: "Light", description: "1–3 days/week" },
  { value: "moderate", label: "Moderate", description: "3–5 days/week" },
  { value: "active", label: "Active", description: "6–7 days/week" },
  { value: "very_active", label: "Very Active", description: "Physical job or 2×/day" },
];

const REPORT_STYLES: { value: ReportStyle; label: string; description: string; emoji: string }[] = [
  { value: "motivational", label: "Motivational", description: "Encouraging & energizing", emoji: "🔥" },
  { value: "analytical", label: "Analytical", description: "Data-driven & precise", emoji: "📊" },
  { value: "brief", label: "Brief", description: "Short & to the point", emoji: "⚡" },
  { value: "detailed", label: "Detailed", description: "Deep dive & thorough", emoji: "📋" },
];

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-7 h-7 rounded-lg bg-surface-elevated flex items-center justify-center">
        <Icon className="w-3.5 h-3.5 text-emerald-400" />
      </div>
      <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">{title}</h2>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs text-text-muted font-medium">{label}</label>
      <div className="flex items-center gap-2 bg-surface-elevated border border-border rounded-xl px-3 py-2.5 focus-within:border-emerald-500/50 transition-colors">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          min={min}
          max={max}
          step={step}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none tabular-nums"
        />
        {unit && <span className="text-xs text-text-muted">{unit}</span>}
      </div>
    </div>
  );
}

function Toggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        "relative w-11 h-6 rounded-full transition-colors duration-200",
        enabled ? "bg-emerald-500" : "bg-surface-elevated border border-border"
      )}
    >
      <motion.div
        className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm"
        animate={{ left: enabled ? "calc(100% - 1.375rem)" : "0.125rem" }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
      />
    </button>
  );
}

function SaveButton({
  onSave,
  saving,
  dirty,
}: {
  onSave: () => void;
  saving: boolean;
  dirty: boolean;
}) {
  if (!dirty) return null;
  return (
    <motion.button
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      onClick={onSave}
      disabled={saving}
      className="flex items-center gap-2 bg-emerald-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-glow-emerald disabled:opacity-60 hover:bg-emerald-400 transition-colors"
    >
      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
      {saving ? "Saving…" : "Save changes"}
    </motion.button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { user, setUser, logout } = useAuthStore();
  const router = useRouter();

  // ── Profile form state ─────────────────────────────────────────────────────
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [goal, setGoal] = useState(user?.goal ?? "maintain");
  const [activityLevel, setActivityLevel] = useState(user?.activity_level ?? "moderate");
  const [age, setAge] = useState(user?.age?.toString() ?? "");
  const [heightCm, setHeightCm] = useState(user?.height_cm?.toString() ?? "");
  const [weightKg, setWeightKg] = useState(user?.weight_kg?.toString() ?? "");
  const [gender, setGender] = useState<string>(user?.gender ?? "");
  const [stepsTarget, setStepsTarget] = useState((user?.daily_steps_target ?? 10000).toString());
  const [targetCalories, setTargetCalories] = useState(user?.target_calories?.toString() ?? "");
  const [targetProtein, setTargetProtein] = useState(user?.target_protein_g?.toString() ?? "");
  const [targetCarbs, setTargetCarbs] = useState(user?.target_carbs_g?.toString() ?? "");
  const [targetFat, setTargetFat] = useState(user?.target_fat_g?.toString() ?? "");

  // ── AI preferences (local, sent on report generation) ─────────────────────
  const [reportStyle, setReportStyle] = useState<ReportStyle>("motivational");
  const [reportEnabled, setReportEnabled] = useState(true);

  // ── Notifications (local UI only) ──────────────────────────────────────────
  const [mealReminders, setMealReminders] = useState(true);
  const [streakAlerts, setStreakAlerts] = useState(true);

  // ── UI state ───────────────────────────────────────────────────────────────
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [editingName, setEditingName] = useState(false);

  // Detect changes against original user data
  const dirty =
    displayName !== (user?.display_name ?? "") ||
    goal !== (user?.goal ?? "maintain") ||
    activityLevel !== (user?.activity_level ?? "moderate") ||
    age !== (user?.age?.toString() ?? "") ||
    heightCm !== (user?.height_cm?.toString() ?? "") ||
    weightKg !== (user?.weight_kg?.toString() ?? "") ||
    gender !== (user?.gender ?? "") ||
    stepsTarget !== ((user?.daily_steps_target ?? 10000).toString()) ||
    targetCalories !== (user?.target_calories?.toString() ?? "") ||
    targetProtein !== (user?.target_protein_g?.toString() ?? "") ||
    targetCarbs !== (user?.target_carbs_g?.toString() ?? "") ||
    targetFat !== (user?.target_fat_g?.toString() ?? "");

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await authApi.updateProfile({
        display_name: displayName || undefined,
        goal: goal as any,
        activity_level: activityLevel as any,
        age: age ? parseInt(age) : undefined,
        height_cm: heightCm ? parseFloat(heightCm) : undefined,
        weight_kg: weightKg ? parseFloat(weightKg) : undefined,
        gender: (gender || undefined) as any,
        daily_steps_target: stepsTarget ? parseInt(stepsTarget) : undefined,
        target_calories: targetCalories ? parseFloat(targetCalories) : undefined,
        target_protein_g: targetProtein ? parseFloat(targetProtein) : undefined,
        target_carbs_g: targetCarbs ? parseFloat(targetCarbs) : undefined,
        target_fat_g: targetFat ? parseFloat(targetFat) : undefined,
      });
      setUser(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      // Invalidate SWR caches that depend on user targets
      mutate("streak");
      mutate(["daily", new Date().toISOString().split("T")[0]]);
    } catch (err: any) {
      setSaveError(err.message ?? "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  // ── Avatar ─────────────────────────────────────────────────────────────────
  const initials = (user?.display_name ?? "U")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const stagger = { visible: { transition: { staggerChildren: 0.06 } } };
  const fadeUp = {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
  };

  return (
    <div className="px-4 pt-12 pb-28 space-y-6 max-w-md mx-auto">
      {/* Page title */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-2xl font-bold text-text-primary">Profile</h1>
        <p className="text-sm text-text-muted mt-0.5">Manage your account and preferences</p>
      </motion.div>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
        className="space-y-5"
      >
        {/* ── Avatar + name card ──────────────────────────────────────────── */}
        <motion.div variants={fadeUp} className="card-surface p-5">
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                <span className="text-xl font-bold text-emerald-400">{initials}</span>
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                <Check className="w-2.5 h-2.5 text-white" />
              </div>
            </div>

            {/* Name + email */}
            <div className="flex-1 min-w-0">
              {editingName ? (
                <div className="flex items-center gap-2">
                  <input
                    autoFocus
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    onBlur={() => setEditingName(false)}
                    onKeyDown={(e) => e.key === "Enter" && setEditingName(false)}
                    className="flex-1 bg-surface-elevated border border-emerald-500/50 rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none"
                  />
                  <button
                    onClick={() => setEditingName(false)}
                    className="text-text-muted hover:text-text-primary"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setEditingName(true)}
                  className="flex items-center gap-1.5 group text-left"
                >
                  <p className="font-semibold text-text-primary truncate">{displayName || "Your Name"}</p>
                  <Pencil className="w-3 h-3 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </button>
              )}
              <p className="text-xs text-text-muted truncate mt-0.5">{user?.email}</p>
              <p className="text-[10px] text-text-muted mt-1">
                Member since {user?.created_at ? new Date(user.created_at).getFullYear() : "—"}
              </p>
            </div>

            {/* Goal badge */}
            <div className="flex flex-col items-end gap-1">
              <span className="text-lg">
                {GOAL_OPTIONS.find((g) => g.value === goal)?.emoji ?? "⚖️"}
              </span>
              <span className="text-[10px] text-text-muted whitespace-nowrap">
                {GOAL_LABELS[goal] ?? goal}
              </span>
            </div>
          </div>
        </motion.div>

        {/* ── Body Stats ──────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Scale} title="Body Stats" />
          <div className="card-surface p-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <NumberField
                label="Age"
                value={age}
                onChange={setAge}
                min={10}
                max={120}
                unit="yrs"
                placeholder="—"
              />
              <NumberField
                label="Height"
                value={heightCm}
                onChange={setHeightCm}
                min={50}
                max={300}
                step={0.1}
                unit="cm"
                placeholder="—"
              />
              <NumberField
                label="Weight"
                value={weightKg}
                onChange={setWeightKg}
                min={20}
                max={500}
                step={0.1}
                unit="kg"
                placeholder="—"
              />
            </div>
            <p className="text-[10px] text-text-muted">
              Body stats are used to auto-calculate your TDEE when no manual calorie target is set.
            </p>
          </div>
        </motion.div>

        {/* ── Gender + Steps Target ───────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Zap} title="Activity Settings" />
          <div className="card-surface p-4 space-y-4">
            {/* Gender */}
            <div>
              <p className="text-xs text-text-muted font-medium mb-2">
                GENDER <span className="text-text-muted/60">(for accurate BMR)</span>
              </p>
              <div className="grid grid-cols-3 gap-2">
                {(["male", "female", "other"] as const).map((g) => (
                  <button
                    key={g}
                    onClick={() => setGender(gender === g ? "" : g)}
                    className={cn(
                      "py-2.5 rounded-xl border text-sm font-medium transition-all capitalize",
                      gender === g
                        ? "bg-blue-500/15 border-blue-500/40 text-blue-400"
                        : "bg-surface-elevated border-border text-text-muted hover:border-blue-500/20"
                    )}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
            {/* Steps target */}
            <NumberField
              label="Daily Steps Target"
              value={stepsTarget}
              onChange={setStepsTarget}
              min={1000}
              max={100000}
              unit="steps"
              placeholder="10000"
            />
          </div>
        </motion.div>

        {/* ── Fitness Goal ────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Target} title="Fitness Goal" />
          <div className="grid grid-cols-2 gap-2">
            {GOAL_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setGoal(opt.value as any)}
                className={cn(
                  "flex flex-col items-start gap-1 p-3 rounded-2xl border transition-all text-left",
                  goal === opt.value
                    ? "bg-emerald-500/15 border-emerald-500/40"
                    : "bg-surface border-border hover:border-emerald-500/20"
                )}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-base">{opt.emoji}</span>
                  {goal === opt.value && (
                    <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center">
                      <Check className="w-2.5 h-2.5 text-white" />
                    </div>
                  )}
                </div>
                <p className={cn(
                  "text-xs font-semibold",
                  goal === opt.value ? "text-emerald-400" : "text-text-primary"
                )}>
                  {opt.label}
                </p>
                <p className="text-[10px] text-text-muted leading-snug">{opt.description}</p>
              </button>
            ))}
          </div>
        </motion.div>

        {/* ── Activity Level ──────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Activity} title="Activity Level" />
          <div className="card-surface p-1 space-y-0.5">
            {ACTIVITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setActivityLevel(opt.value as any)}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all",
                  activityLevel === opt.value
                    ? "bg-emerald-500/15"
                    : "hover:bg-surface-elevated"
                )}
              >
                <div className="text-left">
                  <p className={cn(
                    "text-sm font-medium",
                    activityLevel === opt.value ? "text-emerald-400" : "text-text-primary"
                  )}>
                    {opt.label}
                  </p>
                  <p className="text-xs text-text-muted">{opt.description}</p>
                </div>
                {activityLevel === opt.value && (
                  <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </motion.div>

        {/* ── Nutrition Targets ────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Flame} title="Nutrition Targets" />
          <div className="card-surface p-4 space-y-3">
            <NumberField
              label="Daily Calories"
              value={targetCalories}
              onChange={setTargetCalories}
              min={500}
              max={10000}
              unit="kcal"
              placeholder="Auto-calculated"
            />
            <div className="grid grid-cols-3 gap-3">
              <NumberField
                label="Protein"
                value={targetProtein}
                onChange={setTargetProtein}
                min={0}
                max={1000}
                unit="g"
                placeholder="—"
              />
              <NumberField
                label="Carbs"
                value={targetCarbs}
                onChange={setTargetCarbs}
                min={0}
                max={2000}
                unit="g"
                placeholder="—"
              />
              <NumberField
                label="Fat"
                value={targetFat}
                onChange={setTargetFat}
                min={0}
                max={500}
                unit="g"
                placeholder="—"
              />
            </div>

            {/* Current computed targets summary */}
            {(user?.target_calories || user?.target_protein_g) && (
              <div className="mt-1 p-3 bg-surface-elevated rounded-xl">
                <p className="text-[10px] text-text-muted mb-2 font-medium">CURRENT TARGETS</p>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-sm font-bold tabular-nums text-emerald-400">
                      {user.target_calories ? formatCalories(user.target_calories) : "—"}
                    </p>
                    <p className="text-[10px] text-text-muted">kcal</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-bold tabular-nums text-blue-400">
                      {user.target_protein_g ? `${Math.round(user.target_protein_g)}g` : "—"}
                    </p>
                    <p className="text-[10px] text-text-muted">protein</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-bold tabular-nums text-amber-400">
                      {user.target_carbs_g ? `${Math.round(user.target_carbs_g)}g` : "—"}
                    </p>
                    <p className="text-[10px] text-text-muted">carbs</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-bold tabular-nums text-violet-400">
                      {user.target_fat_g ? `${Math.round(user.target_fat_g)}g` : "—"}
                    </p>
                    <p className="text-[10px] text-text-muted">fat</p>
                  </div>
                </div>
              </div>
            )}

            <p className="text-[10px] text-text-muted">
              Leave calories blank to auto-calculate from your body stats and activity level.
            </p>
          </div>
        </motion.div>

        {/* ── AI Preferences ───────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Brain} title="AI Preferences" />
          <div className="card-surface overflow-hidden">
            {/* Report enabled toggle */}
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-border">
              <div>
                <p className="text-sm font-medium text-text-primary">Daily AI Reports</p>
                <p className="text-xs text-text-muted mt-0.5">Get personalized insights each day</p>
              </div>
              <Toggle enabled={reportEnabled} onToggle={() => setReportEnabled(!reportEnabled)} />
            </div>

            {/* Report style */}
            <AnimatePresence>
              {reportEnabled && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-4">
                    <p className="text-xs text-text-muted font-medium mb-3">REPORT STYLE</p>
                    <div className="grid grid-cols-2 gap-2">
                      {REPORT_STYLES.map((style) => (
                        <button
                          key={style.value}
                          onClick={() => setReportStyle(style.value)}
                          className={cn(
                            "flex items-start gap-2.5 p-3 rounded-xl border text-left transition-all",
                            reportStyle === style.value
                              ? "bg-indigo-500/15 border-indigo-500/40"
                              : "bg-surface-elevated border-transparent hover:border-border"
                          )}
                        >
                          <span className="text-base flex-shrink-0">{style.emoji}</span>
                          <div className="min-w-0">
                            <p className={cn(
                              "text-xs font-semibold",
                              reportStyle === style.value ? "text-indigo-400" : "text-text-primary"
                            )}>
                              {style.label}
                            </p>
                            <p className="text-[10px] text-text-muted leading-snug mt-0.5">
                              {style.description}
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* ── Notifications ────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <SectionHeader icon={Bell} title="Notifications" />
          <div className="card-surface divide-y divide-border">
            <div className="flex items-center justify-between px-4 py-3.5">
              <div>
                <p className="text-sm font-medium text-text-primary">Meal Reminders</p>
                <p className="text-xs text-text-muted mt-0.5">Nudge to log at breakfast, lunch & dinner</p>
              </div>
              <Toggle enabled={mealReminders} onToggle={() => setMealReminders(!mealReminders)} />
            </div>
            <div className="flex items-center justify-between px-4 py-3.5">
              <div>
                <p className="text-sm font-medium text-text-primary">Streak Alerts</p>
                <p className="text-xs text-text-muted mt-0.5">Get reminded before your streak breaks</p>
              </div>
              <Toggle enabled={streakAlerts} onToggle={() => setStreakAlerts(!streakAlerts)} />
            </div>
          </div>
        </motion.div>

        {/* ── Health Connect ───────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <div className="card-surface p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-500/10 border border-rose-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-lg">❤️</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary">Health Connect</p>
                <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
                  Sync workouts and body metrics from Google Health Connect or Apple Health.
                </p>
                <button className="mt-2.5 flex items-center gap-1.5 text-xs font-medium text-rose-400 hover:text-rose-300 transition-colors">
                  Connect Health App
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex-shrink-0">
                <span className="text-[10px] bg-zinc-700/60 text-zinc-400 px-2 py-0.5 rounded-full font-medium">
                  Coming soon
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── App info ─────────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <div className="card-surface divide-y divide-border">
            <button className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-surface-elevated/50 transition-colors">
              <p className="text-sm text-text-secondary">Privacy Policy</p>
              <ChevronRight className="w-4 h-4 text-text-muted" />
            </button>
            <button className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-surface-elevated/50 transition-colors">
              <p className="text-sm text-text-secondary">Terms of Service</p>
              <ChevronRight className="w-4 h-4 text-text-muted" />
            </button>
            <div className="flex items-center justify-between px-4 py-3.5">
              <p className="text-sm text-text-muted">Version</p>
              <p className="text-sm text-text-muted tabular-nums">1.0.0</p>
            </div>
          </div>
        </motion.div>

        {/* ── Log out ──────────────────────────────────────────────────────── */}
        <motion.div variants={fadeUp}>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-400 hover:bg-rose-500/15 transition-colors font-medium text-sm"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </motion.div>
      </motion.div>

      {/* ── Sticky save bar ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {(dirty || saveSuccess) && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 flex flex-col items-center gap-2"
          >
            {saveSuccess ? (
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                className="flex items-center gap-2 bg-emerald-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-glow-emerald"
              >
                <Check className="w-4 h-4" />
                Profile saved!
              </motion.div>
            ) : (
              <>
                <SaveButton onSave={handleSave} saving={saving} dirty={dirty} />
                {saveError && (
                  <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-1.5">
                    {saveError}
                  </p>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

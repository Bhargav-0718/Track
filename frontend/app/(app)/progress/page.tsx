"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Camera, Scale, Calendar, X,
  ChevronRight, Loader2, Sparkles, Info
} from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { format, parseISO } from "date-fns";
import Image from "next/image";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine
} from "recharts";

import { checkpointsApi } from "@/lib/api/checkpoints";
import { analyticsApi } from "@/lib/api/analytics";
import { formatKg, formatDateShort, todayISO, cn } from "@/lib/utils/format";
import type { CheckpointSummary, CompareResponse } from "@/lib/types";

// ── Weight chart ──────────────────────────────────────────────────────────────

function WeightChart({ checkpoints }: { checkpoints: CheckpointSummary[] }) {
  const data = checkpoints
    .filter((c) => c.weight_kg)
    .sort((a, b) => a.checkpoint_date.localeCompare(b.checkpoint_date))
    .map((c) => ({
      date: format(parseISO(c.checkpoint_date), "MMM d"),
      weight: c.weight_kg,
    }));

  if (data.length < 2) return null;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="glass rounded-xl px-3 py-2 text-xs">
        <p className="text-text-primary font-bold">{payload[0].value} kg</p>
        <p className="text-text-muted">{payload[0].payload.date}</p>
      </div>
    );
  };

  return (
    <div className="card-surface p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-secondary">Weight Trend</h3>
        {data.length >= 2 && (
          <span
            className={cn(
              "text-xs font-medium px-2 py-0.5 rounded-full",
              (data[data.length - 1].weight! - data[0].weight!) < 0
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-zinc-700/50 text-zinc-400"
            )}
          >
            {(data[data.length - 1].weight! - data[0].weight!).toFixed(1)} kg
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: -32, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={["dataMin - 1", "dataMax + 1"]}
            tick={{ fontSize: 10, fill: "#71717a" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="weight"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: "#10b981", r: 4, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: "#10b981", strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Comparison modal ──────────────────────────────────────────────────────────

function CompareModal({
  checkpoints,
  onClose,
}: {
  checkpoints: CheckpointSummary[];
  onClose: () => void;
}) {
  const withPhotos = checkpoints.filter((c) => c.photo_count > 0);
  const [beforeId, setBeforeId] = useState<string>(withPhotos[0]?.id ?? "");
  const [afterId, setAfterId] = useState<string>(withPhotos[withPhotos.length - 1]?.id ?? "");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare() {
    if (!beforeId || !afterId || beforeId === afterId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await checkpointsApi.compare(beforeId, afterId);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  }

  const beforeCp = checkpoints.find((c) => c.id === beforeId);
  const afterCp = checkpoints.find((c) => c.id === afterId);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end"
      onClick={onClose}
    >
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
        className="w-full max-h-[90dvh] overflow-y-auto bg-surface rounded-t-3xl p-5 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle */}
        <div className="w-10 h-1 bg-surface-elevated rounded-full mx-auto" />

        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Compare Progress</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-secondary">
            <X className="w-5 h-5" />
          </button>
        </div>

        {withPhotos.length < 2 ? (
          <div className="text-center py-8 space-y-2">
            <p className="text-4xl">📸</p>
            <p className="text-text-secondary font-medium">Need at least 2 checkpoints with photos</p>
            <p className="text-sm text-text-muted">Upload photos to 2+ checkpoints to compare</p>
          </div>
        ) : (
          <>
            {/* Before / After selectors */}
            <div className="grid grid-cols-2 gap-3">
              {["Before", "After"].map((label, idx) => {
                const id = idx === 0 ? beforeId : afterId;
                const cp = checkpoints.find((c) => c.id === id);
                return (
                  <div key={label}>
                    <p className="text-xs text-text-muted mb-2">{label}</p>
                    <select
                      value={id}
                      onChange={(e) =>
                        idx === 0 ? setBeforeId(e.target.value) : setAfterId(e.target.value)
                      }
                      className="w-full bg-surface-elevated border border-border rounded-xl
                                 px-3 py-2 text-xs text-text-primary
                                 focus:outline-none focus:border-emerald-500/50"
                    >
                      {withPhotos.map((c) => (
                        <option key={c.id} value={c.id}>
                          {format(parseISO(c.checkpoint_date), "MMM d, yyyy")}
                          {c.weight_kg ? ` · ${c.weight_kg}kg` : ""}
                        </option>
                      ))}
                    </select>
                    {cp?.primary_photo_url && (
                      <div className="mt-2 rounded-xl overflow-hidden aspect-[3/4] relative bg-surface-elevated">
                        <Image
                          src={`http://localhost:8000${cp.primary_photo_url}`}
                          alt={label}
                          fill
                          className="object-cover"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <button
              onClick={handleCompare}
              disabled={loading || beforeId === afterId || !beforeId || !afterId}
              className="w-full bg-indigo-500 hover:bg-indigo-600
                         text-white font-medium rounded-xl py-3 text-sm
                         flex items-center justify-center gap-2
                         transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing with AI...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Analyze with AI
                </>
              )}
            </button>

            {error && <p className="text-red-400 text-sm text-center">{error}</p>}

            {/* AI Result */}
            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4"
                >
                  {/* Overall */}
                  <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-4 h-4 text-indigo-400" />
                      <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wide">
                        AI Analysis
                      </span>
                      <span className={cn(
                        "ml-auto text-xs px-2 py-0.5 rounded-full font-medium",
                        result.overall_progress === "significant_progress"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : result.overall_progress === "steady_progress"
                          ? "bg-blue-500/15 text-blue-400"
                          : "bg-zinc-700/50 text-zinc-400"
                      )}>
                        {result.overall_progress.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {result.overall_summary}
                    </p>
                  </div>

                  {/* Weight delta */}
                  {result.weight_delta_kg != null && (
                    <div className="card-surface px-4 py-3 flex items-center justify-between">
                      <span className="text-sm text-text-secondary">Weight change</span>
                      <span className={cn(
                        "text-sm font-bold",
                        result.weight_delta_kg < 0 ? "text-emerald-400" : "text-zinc-400"
                      )}>
                        {result.weight_delta_kg > 0 ? "+" : ""}{result.weight_delta_kg.toFixed(1)} kg
                      </span>
                    </div>
                  )}

                  {/* Observations */}
                  <div className="space-y-2">
                    {result.observations.map((obs, i) => (
                      <div key={i} className="card-surface px-4 py-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-semibold text-text-muted uppercase">
                            {obs.category.replace(/_/g, " ")}
                          </span>
                          {obs.direction === "positive" && (
                            <span className="text-emerald-400 text-xs">↑</span>
                          )}
                        </div>
                        <p className="text-sm text-text-secondary">{obs.observation}</p>
                      </div>
                    ))}
                  </div>

                  {/* Encouragement */}
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-4">
                    <p className="text-sm text-emerald-300 font-medium">{result.encouragement}</p>
                  </div>

                  {/* Disclaimer */}
                  <div className="flex gap-2 text-xs text-text-muted">
                    <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <p>{result.disclaimer}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}

// ── Checkpoint card ───────────────────────────────────────────────────────────

function CheckpointCard({
  checkpoint,
  onPhotoUpload,
}: {
  checkpoint: CheckpointSummary;
  onPhotoUpload: (id: string, file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const inputRef2 = useState<HTMLInputElement | null>(null);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface overflow-hidden"
    >
      <div className="flex gap-3 p-4">
        {/* Photo thumbnail / upload */}
        <div
          className="w-20 h-24 rounded-xl bg-surface-elevated flex items-center justify-center
                     relative overflow-hidden shrink-0 cursor-pointer"
          onClick={() => {
            const el = document.getElementById(`photo-input-${checkpoint.id}`) as HTMLInputElement;
            el?.click();
          }}
        >
          {checkpoint.primary_photo_url ? (
            <Image
              src={`http://localhost:8000${checkpoint.primary_photo_url}`}
              alt="Progress photo"
              fill
              className="object-cover"
            />
          ) : (
            <div className="flex flex-col items-center gap-1 text-text-muted">
              <Camera className="w-5 h-5" />
              <span className="text-[10px]">Add photo</span>
            </div>
          )}
          <input
            id={`photo-input-${checkpoint.id}`}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onPhotoUpload(checkpoint.id, file);
            }}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-text-primary">
                {formatDateShort(checkpoint.checkpoint_date)}
              </p>
              {checkpoint.weight_kg && (
                <p className="text-xl font-bold text-text-primary tabular-nums mt-0.5">
                  {checkpoint.weight_kg}
                  <span className="text-sm text-text-muted font-normal"> kg</span>
                </p>
              )}
            </div>
            {checkpoint.photo_count > 0 && (
              <span className="text-xs text-text-muted bg-surface-elevated
                               px-2 py-0.5 rounded-full shrink-0">
                {checkpoint.photo_count} photo{checkpoint.photo_count !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {checkpoint.notes && (
            <p className="text-xs text-text-muted mt-2 line-clamp-2">{checkpoint.notes}</p>
          )}

          {checkpoint.tags?.length > 0 && (
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {checkpoint.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] text-text-muted bg-surface-elevated
                             px-2 py-0.5 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Add checkpoint modal ──────────────────────────────────────────────────────

function AddCheckpointModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [form, setForm] = useState({
    checkpoint_date: todayISO(),
    weight_kg: "",
    notes: "",
    tags: "",
  });
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await checkpointsApi.create({
        checkpoint_date: form.checkpoint_date,
        weight_kg: form.weight_kg ? parseFloat(form.weight_kg) : undefined,
        notes: form.notes || undefined,
        tags: form.tags ? form.tags.split(",").map((t) => t.trim()) : [],
      });
      onAdded();
      onClose();
    } catch {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end"
      onClick={onClose}
    >
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
        className="w-full bg-surface rounded-t-3xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-10 h-1 bg-surface-elevated rounded-full mx-auto mb-5" />
        <h2 className="text-lg font-bold mb-5">New Checkpoint</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: "checkpoint_date", label: "Date", type: "date" },
            { key: "weight_kg", label: "Weight (kg)", type: "number", placeholder: "75.5" },
            { key: "notes", label: "Notes", type: "text", placeholder: "End of week 4..." },
            { key: "tags", label: "Tags (comma-separated)", type: "text", placeholder: "end-of-cut, 12-week" },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm text-text-secondary mb-1">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full bg-surface-elevated border border-border rounded-xl
                           px-4 py-3 text-sm text-text-primary
                           placeholder:text-text-muted
                           focus:outline-none focus:border-emerald-500/50 transition-all"
              />
            </div>
          ))}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-white
                       font-medium rounded-xl py-3 text-sm
                       flex items-center justify-center gap-2
                       transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "Save Checkpoint"
            )}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

import { useRef } from "react";

export default function ProgressPage() {
  const { mutate } = useSWRConfig();
  const [showAdd, setShowAdd] = useState(false);
  const [showCompare, setShowCompare] = useState(false);

  const { data, mutate: mutateCheckpoints } = useSWR(
    "checkpoints",
    () => checkpointsApi.list({ page_size: 50 })
  );

  const checkpoints = data?.items ?? [];

  async function handlePhotoUpload(checkpointId: string, file: File) {
    try {
      await checkpointsApi.uploadPhoto(checkpointId, file);
      mutateCheckpoints();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="px-4 pt-12 pb-4 max-w-md mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Progress</h1>
          <p className="text-text-muted text-sm">{checkpoints.length} checkpoints</p>
        </div>
        <div className="flex items-center gap-2">
          {checkpoints.filter((c) => c.photo_count > 0).length >= 2 && (
            <button
              onClick={() => setShowCompare(true)}
              className="flex items-center gap-1.5 text-sm text-indigo-400
                         bg-indigo-500/10 border border-indigo-500/20
                         rounded-xl px-3 py-2 hover:bg-indigo-500/15 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Compare
            </button>
          )}
          <button
            onClick={() => setShowAdd(true)}
            className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center
                       hover:bg-emerald-600 transition-colors"
          >
            <Plus className="w-4.5 h-4.5 text-white" strokeWidth={2.5} />
          </button>
        </div>
      </div>

      {/* Weight chart */}
      {checkpoints.length >= 2 && <WeightChart checkpoints={checkpoints} />}

      {/* Checkpoints list */}
      {checkpoints.length > 0 ? (
        <div className="space-y-3">
          {[...checkpoints]
            .sort((a, b) => b.checkpoint_date.localeCompare(a.checkpoint_date))
            .map((cp) => (
              <CheckpointCard
                key={cp.id}
                checkpoint={cp}
                onPhotoUpload={handlePhotoUpload}
              />
            ))}
        </div>
      ) : (
        <div className="text-center py-16 space-y-3">
          <p className="text-5xl">📸</p>
          <p className="text-text-secondary font-semibold">No checkpoints yet</p>
          <p className="text-sm text-text-muted max-w-[220px] mx-auto">
            Add your first checkpoint to start tracking your transformation
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="mt-2 bg-emerald-500/15 border border-emerald-500/30
                       text-emerald-400 text-sm font-medium
                       rounded-xl px-5 py-2.5 hover:bg-emerald-500/20 transition-colors"
          >
            Add First Checkpoint
          </button>
        </div>
      )}

      {/* Modals */}
      <AnimatePresence>
        {showAdd && (
          <AddCheckpointModal
            onClose={() => setShowAdd(false)}
            onAdded={() => mutateCheckpoints()}
          />
        )}
        {showCompare && (
          <CompareModal
            checkpoints={checkpoints}
            onClose={() => setShowCompare(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

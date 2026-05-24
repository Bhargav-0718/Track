import { api } from "./client";
import type { StepLog, StepHistoryResponse } from "../types";

export const activityApi = {
  /** Upsert today's (or a given date's) step count */
  logSteps: (steps: number, date?: string) =>
    api.post<StepLog>("/api/v1/activity/steps", {
      steps,
      ...(date ? { date } : {}),
    }),

  /** Get last N days of step history */
  getHistory: (days = 7) =>
    api.get<StepHistoryResponse>(`/api/v1/activity/steps?days=${days}`),
};

// ── Pure calculation helpers ───────────────────────────────────────────────────

/** Mifflin-St Jeor BMR (kcal/day) */
export function calculateBmr(
  weightKg: number,
  heightCm: number,
  age: number,
  gender: string
): number {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age;
  if (gender === "male") return base + 5;
  if (gender === "female") return base - 161;
  return base - 78; // midpoint for 'other'
}

/** Approximate distance in km */
export function stepsToKm(steps: number, heightCm: number): number {
  const strideLengthM = (heightCm * 0.415) / 100;
  return (steps * strideLengthM) / 1000;
}

/** Approximate active calories burned from walking */
export function stepsToCalories(
  steps: number,
  weightKg: number,
  heightCm: number
): number {
  const distanceKm = stepsToKm(steps, heightCm);
  return distanceKm * weightKg * 1.036;
}

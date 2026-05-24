// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  age: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  gender: "male" | "female" | "other" | null;
  daily_steps_target: number | null;
  activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active";
  goal: "lose_weight" | "maintain" | "gain_muscle" | "improve_fitness";
  target_calories: number | null;
  target_protein_g: number | null;
  target_carbs_g: number | null;
  target_fat_g: number | null;
  is_active: boolean;
  created_at: string;
}

// ── Activity / Step Logs ───────────────────────────────────────────────────────

export interface StepLog {
  id: string;
  date: string;          // "YYYY-MM-DD"
  steps: number;
  created_at: string;
  updated_at: string;
}

export interface StepHistoryResponse {
  items: StepLog[];
  total: number;
}

// ── Food Logs ─────────────────────────────────────────────────────────────────

export type MealType =
  | "breakfast"
  | "lunch"
  | "dinner"
  | "snack"
  | "pre_workout"
  | "post_workout";

export type EstimationSource =
  | "memory"
  | "dataset"
  | "llm"
  | "manual"
  | "photo"
  | "health_connect";

export type ConfidenceLevel = "confirmed" | "estimated" | "uncertain";

export interface FoodLog {
  id: string;
  user_id: string;
  food_name: string;
  brand_name: string | null;
  raw_input: string | null;
  meal_type: MealType;
  portion_description: string | null;
  portion_grams: number | null;
  calories: number;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  estimation_source: EstimationSource;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  assumptions: string[];
  is_corrected: boolean;
  logged_at: string;
  created_at: string;
}

export interface FoodLogCreate {
  raw_input?: string;
  food_name?: string;
  calories?: number;
  meal_type: MealType;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
  fiber_g?: number;
  portion_description?: string;
  portion_grams?: number;
  logged_at?: string;
}

export interface DailyFoodSummary {
  date: string;
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  food_count: number;
  logs: FoodLog[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ── Workout Logs ──────────────────────────────────────────────────────────────

export type WorkoutType = "strength" | "cardio" | "hiit" | "yoga" | "sports" | "other";
export type Intensity = "low" | "moderate" | "high" | "very_high";

export interface Exercise {
  name: string;
  sets?: number;
  reps?: number;
  weight_kg?: number;
  duration_seconds?: number;
}

export interface WorkoutLog {
  id: string;
  user_id: string;
  title: string;
  workout_type: WorkoutType;
  duration_minutes: number;
  intensity: Intensity;
  calories_burned: number | null;
  exercises: Exercise[];
  notes: string | null;
  logged_at: string;
}

export interface WorkoutLogCreate {
  title: string;
  workout_type: WorkoutType;
  duration_minutes: number;
  intensity: Intensity;
  exercises?: Exercise[];
  notes?: string;
  logged_at?: string;
}

// ── Progress Checkpoints ──────────────────────────────────────────────────────

export interface ProgressPhoto {
  id: string;
  checkpoint_id: string;
  url: string;
  original_filename: string | null;
  content_type: string;
  file_size_bytes: number;
  width_px: number;
  height_px: number;
  display_order: number;
  label: string | null;
  created_at: string;
}

export interface ProgressCheckpoint {
  id: string;
  checkpoint_date: string;
  weight_kg: number | null;
  body_fat_percentage: number | null;
  notes: string | null;
  tags: string[];
  photos: ProgressPhoto[];
  created_at: string;
  updated_at: string;
}

export interface CheckpointSummary {
  id: string;
  checkpoint_date: string;
  weight_kg: number | null;
  body_fat_percentage: number | null;
  notes: string | null;
  tags: string[];
  photo_count: number;
  primary_photo_url: string | null;
  created_at: string;
}

export interface CheckpointCreate {
  checkpoint_date: string;
  weight_kg?: number;
  body_fat_percentage?: number;
  notes?: string;
  tags?: string[];
}

export interface PhysiqueObservation {
  category: "overall" | "fat_distribution" | "muscle_definition" | "posture" | "waistline" | "consistency";
  observation: string;
  direction: "positive" | "neutral" | "insufficient_data";
}

export interface CompareResponse {
  before_checkpoint_id: string;
  after_checkpoint_id: string;
  before_date: string;
  after_date: string;
  days_elapsed: number;
  weight_delta_kg: number | null;
  overall_summary: string;
  observations: PhysiqueObservation[];
  encouragement: string;
  confidence_note: string;
  overall_progress: "significant_progress" | "steady_progress" | "maintenance" | "insufficient_data";
  disclaimer: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface StreakInfo {
  current_streak_days: number;
  longest_streak_days: number;
  streak_started_on: string | null;
  last_logged_date: string | null;
  is_active_today: boolean;
}

export interface ConsistencyBreakdown {
  overall_score: number;
  logging_consistency: number;
  calorie_adherence: number;
  protein_adherence: number;
  workout_consistency: number;
  period_days: number;
  period_label: "7d" | "30d";
  days_logged: number;
  days_in_period: number;
  workouts_completed: number;
}

export interface DailyDataPoint {
  date: string;
  calories: number;
  protein_g: number | null;
  workouts: number;
  logged: boolean;
  consistency_score: number | null;
}

export interface TrendResponse {
  period_days: number;
  data_points: DailyDataPoint[];
  calorie_target: number | null;
  protein_target_g: number | null;
  average_calories: number;
  average_protein_g: number | null;
}

export interface MealAdherencePattern {
  meal_type: string;
  log_frequency_pct: number;
  avg_calories: number;
  most_common_foods: string[];
}

export interface EstimationAccuracyStats {
  total_logs: number;
  corrected_logs: number;
  correction_rate_pct: number;
  avg_calorie_delta: number;
  source_breakdown: Record<string, number>;
}

export interface AnalyticsSummary {
  user_id: string;
  streak: StreakInfo;
  consistency_7d: ConsistencyBreakdown;
  consistency_30d: ConsistencyBreakdown;
  meal_patterns: MealAdherencePattern[];
  estimation_accuracy: EstimationAccuracyStats;
  pattern_insights: string[];
  checkpoints_count: number;
  latest_weight_kg: number | null;
  weight_trend_kg: number | null;
  computed_at: string;
}

// ── Daily Reports ─────────────────────────────────────────────────────────────

export type ReportStyle = "motivational" | "analytical" | "brief" | "detailed";

export interface DailyReport {
  id: string;
  report_date: string;
  calorie_summary: {
    target: number;
    actual: number;
    adherence_pct: number;
    deficit_or_surplus: number;
  };
  workout_summary: {
    count: number;
    calories_burned: number;
    net_calories: number;
    types: string[];
    duration_minutes: number;
    rest_day: boolean;
  };
  macro_summary: {
    protein_g: number;
    protein_target_g: number | null;
    carbs_g: number;
    fat_g: number;
  };
  consistency_score: number;
  streak_days: number;
  weekly_consistency: number;
  insights_text: string | null;
  motivation_message: string | null;
  behavioral_observations: string[];
  report_style: ReportStyle;
  was_shown: boolean;
  user_rating: number | null;
  created_at: string;
}

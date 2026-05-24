import { api } from "./client";
import type { WorkoutLog, WorkoutLogCreate, PaginatedResponse } from "../types";

const PREFIX = "/api/v1/workout-logs";

export const workoutApi = {
  createLog: (data: WorkoutLogCreate) =>
    api.post<WorkoutLog>(PREFIX + "/", data),

  listLogs: (params?: {
    page?: number;
    page_size?: number;
    workout_type?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.workout_type) query.set("workout_type", params.workout_type);
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    return api.get<PaginatedResponse<WorkoutLog>>(PREFIX + "/?" + query.toString());
  },

  getRecent: (limit = 20) =>
    api.get<PaginatedResponse<WorkoutLog>>(PREFIX + `/?page_size=${limit}`),

  getLog: (id: string) =>
    api.get<WorkoutLog>(PREFIX + `/${id}`),

  deleteLog: (id: string) =>
    api.delete<void>(PREFIX + `/${id}`),
};

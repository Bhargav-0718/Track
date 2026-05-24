import { api } from "./client";
import type {
  DailyFoodSummary,
  FoodLog,
  FoodLogCreate,
  PaginatedResponse,
} from "../types";

const PREFIX = "/api/v1/food-logs";

export const foodApi = {
  createLog: (data: FoodLogCreate) =>
    api.post<FoodLog>(PREFIX + "/", data),

  getDaily: (date?: string) =>
    api.get<DailyFoodSummary>(
      PREFIX + "/daily" + (date ? `?date=${date}` : "")
    ),

  listLogs: (params?: {
    page?: number;
    page_size?: number;
    meal_type?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.meal_type) query.set("meal_type", params.meal_type);
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    return api.get<PaginatedResponse<FoodLog>>(
      PREFIX + "/?" + query.toString()
    );
  },

  getRecent: (limit = 20) =>
    api.get<FoodLog[]>(PREFIX + `/recent?limit=${limit}`),

  getLog: (id: string) =>
    api.get<FoodLog>(PREFIX + `/${id}`),

  updateLog: (id: string, data: Partial<FoodLogCreate>) =>
    api.put<FoodLog>(PREFIX + `/${id}`, data),

  deleteLog: (id: string) =>
    api.delete<void>(PREFIX + `/${id}`),
};

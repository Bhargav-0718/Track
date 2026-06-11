import { api } from "./client";
import type { UserFoodItem, UserFoodItemUpsert } from "../types";

const PREFIX = "/api/v1/food-items";

export const foodItemsApi = {
  search: (q: string, limit = 10) =>
    api.get<UserFoodItem[]>(
      PREFIX + `/search?q=${encodeURIComponent(q)}&limit=${limit}`
    ),

  list: () => api.get<UserFoodItem[]>(PREFIX + "/"),

  upsert: (data: UserFoodItemUpsert) =>
    api.put<UserFoodItem>(PREFIX + "/", data),

  delete: (id: string) => api.delete<void>(PREFIX + `/${id}`),
};

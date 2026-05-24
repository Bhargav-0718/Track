import { api } from "./client";
import type { AnalyticsSummary, StreakInfo, TrendResponse } from "../types";

const PREFIX = "/api/v1/analytics";

export const analyticsApi = {
  getSummary: () =>
    api.get<AnalyticsSummary>(PREFIX + "/summary"),

  getTrend: (period_days: 7 | 14 | 30 | 90 = 30) =>
    api.get<TrendResponse>(PREFIX + `/trend?period_days=${period_days}`),

  getStreak: () =>
    api.get<StreakInfo>(PREFIX + "/streak"),
};

import { api } from "./client";
import type { DailyReport, ReportStyle } from "../types";

const PREFIX = "/api/v1/reports";

export const reportsApi = {
  generate: (opts?: {
    report_date?: string;
    report_style?: ReportStyle;
    force_regenerate?: boolean;
  }) => api.post<DailyReport>(PREFIX + "/generate", opts ?? {}),

  list: (limit = 30, offset = 0) =>
    api.get<DailyReport[]>(PREFIX + `/?limit=${limit}&offset=${offset}`),

  getByDate: (date: string) =>
    api.get<DailyReport>(PREFIX + `/${date}`),

  markShown: (id: string) =>
    api.post<DailyReport>(PREFIX + `/${id}/shown`, {}),

  rate: (id: string, rating: number) =>
    api.post<DailyReport>(PREFIX + `/${id}/rate`, { rating }),
};

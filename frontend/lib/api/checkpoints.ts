import { api } from "./client";
import type {
  CheckpointCreate,
  CheckpointSummary,
  CompareResponse,
  PaginatedResponse,
  ProgressCheckpoint,
  ProgressPhoto,
} from "../types";

const PREFIX = "/api/v1/checkpoints";

export const checkpointsApi = {
  create: (data: CheckpointCreate) =>
    api.post<ProgressCheckpoint>(PREFIX + "/", data),

  list: (params?: {
    page?: number;
    page_size?: number;
    date_from?: string;
    date_to?: string;
    tags?: string[];
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.date_from) query.set("date_from", params.date_from);
    if (params?.date_to) query.set("date_to", params.date_to);
    params?.tags?.forEach((t) => query.append("tags", t));
    return api.get<PaginatedResponse<CheckpointSummary>>(
      PREFIX + "/?" + query.toString()
    );
  },

  get: (id: string) =>
    api.get<ProgressCheckpoint>(PREFIX + `/${id}`),

  update: (id: string, data: Partial<CheckpointCreate>) =>
    api.patch<ProgressCheckpoint>(PREFIX + `/${id}`, data),

  delete: (id: string) =>
    api.delete<void>(PREFIX + `/${id}`),

  uploadPhoto: (checkpointId: string, file: File, label?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (label) formData.append("label", label);
    return api.upload<ProgressPhoto>(
      PREFIX + `/${checkpointId}/photos`,
      formData
    );
  },

  deletePhoto: (checkpointId: string, photoId: string) =>
    api.delete<void>(PREFIX + `/${checkpointId}/photos/${photoId}`),

  compare: (beforeId: string, afterId: string) =>
    api.post<CompareResponse>(PREFIX + "/compare", {
      before_checkpoint_id: beforeId,
      after_checkpoint_id: afterId,
    }),
};

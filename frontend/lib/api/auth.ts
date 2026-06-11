import { api } from "./client";
import type { AuthTokens, User, UserPreferences } from "../types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    display_name: string;
  }) => api.post<{ user: User; access_token: string }>("/api/v1/auth/register", data),

  login: (email: string, password: string) =>
    api.post<{ user: User; access_token: string }>("/api/v1/auth/login", {
      email,
      password,
    }),

  getProfile: () => api.get<User>("/api/v1/users/me"),

  updateProfile: (data: Partial<User>) =>
    api.put<User>("/api/v1/users/me", data),

  getPreferences: () => api.get<UserPreferences>("/api/v1/users/me/preferences"),

  updatePreferences: (data: Partial<UserPreferences>) =>
    api.put<UserPreferences>("/api/v1/users/me/preferences", data),
};

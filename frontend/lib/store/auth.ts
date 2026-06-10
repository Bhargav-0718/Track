"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../types";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;

  setToken: (token: string) => void;
  setUser: (user: User) => void;
  setHasHydrated: (v: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      hasHydrated: false,

      setToken: (token) => {
        set({ token, isAuthenticated: true });
        if (typeof window !== "undefined") {
          localStorage.setItem("track_token", token);
        }
      },

      setUser: (user) => set({ user }),

      setHasHydrated: (v) => set({ hasHydrated: v }),

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false });
        if (typeof window !== "undefined") {
          localStorage.removeItem("track_token");
        }
      },
    }),
    {
      name: "track-auth",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

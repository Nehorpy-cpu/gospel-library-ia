"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AuthRole = "user" | "admin";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: AuthRole;
};

type AuthState = {
  user?: AuthUser;
  hydrated: boolean;
  setHydrated: (hydrated: boolean) => void;
  signIn: (user: AuthUser) => void;
  signOut: () => void;
};

const COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

function setCookie(name: string, value: string, maxAge = COOKIE_MAX_AGE) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=lax`;
}

function clearCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

function syncAuthCookies(user?: AuthUser) {
  if (!user) {
    clearCookie("gospel_user_id");
    clearCookie("gospel_user_role");
    clearCookie("gospel_user_email");
    clearCookie("gospel_user_name");
    return;
  }
  setCookie("gospel_user_id", user.id);
  setCookie("gospel_user_role", user.role);
  setCookie("gospel_user_email", user.email);
  setCookie("gospel_user_name", user.name);
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: undefined,
      hydrated: false,
      setHydrated: (hydrated) => set({ hydrated }),
      signIn: (user) => {
        syncAuthCookies(user);
        set({ user });
      },
      signOut: () => {
        syncAuthCookies(undefined);
        set({ user: undefined });
      }
    }),
    {
      name: "gospel-auth-storage",
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
        syncAuthCookies(state?.user);
      }
    }
  )
);

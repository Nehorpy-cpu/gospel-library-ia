"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CallingFocus } from "@/lib/church-callings";
import { resolvedCallingName } from "@/lib/church-callings";

type UserPreferencesState = CallingFocus & {
  setCallingFocus: (focus: Partial<CallingFocus>) => void;
  resetCallingFocus: () => void;
  activeCallingName: () => string | undefined;
};

const defaultCallingFocus: CallingFocus = {
  callingCategory: undefined,
  callingName: undefined,
  customCallingName: undefined,
  callingFocusEnabled: false
};

export const useUserPreferencesStore = create<UserPreferencesState>()(
  persist(
    (set, get) => ({
      ...defaultCallingFocus,
      setCallingFocus: (focus) => set((current) => ({ ...current, ...focus })),
      resetCallingFocus: () => set(defaultCallingFocus),
      activeCallingName: () => resolvedCallingName(get())
    }),
    { name: "gospel-library-user-preferences" }
  )
);

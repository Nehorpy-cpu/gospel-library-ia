"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type UIState = {
  sidebarOpen: boolean;
  searchOpen: boolean;
  audioOpen: boolean;
  activeAudioTitle?: string;
  setSidebarOpen: (open: boolean) => void;
  setSearchOpen: (open: boolean) => void;
  setAudio: (open: boolean, title?: string) => void;
};

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      searchOpen: false,
      audioOpen: false,
      activeAudioTitle: undefined,
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setSearchOpen: (searchOpen) => set({ searchOpen }),
      setAudio: (audioOpen, activeAudioTitle) => set({ audioOpen, activeAudioTitle })
    }),
    { name: "gospel-library-ui" }
  )
);


"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type LibraryState = {
  favorites: string[];
  history: string[];
  toggleFavorite: (id: string) => void;
  pushHistory: (id: string) => void;
};

const DEFAULT_STUDY_USER_ID =
  process.env.NEXT_PUBLIC_STUDY_USER_ID ?? "00000000-0000-4000-8000-000000000001";

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set) => ({
      favorites: [],
      history: [],
      toggleFavorite: (id) =>
        set((state) => ({
          favorites: state.favorites.includes(id)
            ? state.favorites.filter((item) => item !== id)
            : [id, ...state.favorites]
        })),
      pushHistory: (id) =>
        set((state) => ({
          history: [id, ...state.history.filter((item) => item !== id)].slice(0, 80)
        }))
    }),
    { name: `gospel-library-state:${DEFAULT_STUDY_USER_ID}` }
  )
);

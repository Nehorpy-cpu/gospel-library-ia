"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type LibraryState = {
  userId: string;
  byUser: Record<string, { favorites: string[]; history: string[] }>;
  favorites: string[];
  history: string[];
  setUserId: (userId: string) => void;
  toggleFavorite: (id: string) => void;
  pushHistory: (id: string) => void;
};

const DEFAULT_STUDY_USER_ID =
  process.env.NEXT_PUBLIC_STUDY_USER_ID ?? "00000000-0000-4000-8000-000000000001";

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set) => ({
      userId: DEFAULT_STUDY_USER_ID,
      byUser: {},
      favorites: [],
      history: [],
      setUserId: (userId) =>
        set((state) => {
          const current = { favorites: state.favorites, history: state.history };
          const next = state.byUser[userId] ?? { favorites: [], history: [] };
          return {
            userId,
            byUser: { ...state.byUser, [state.userId]: current, [userId]: next },
            favorites: next.favorites,
            history: next.history
          };
        }),
      toggleFavorite: (id) =>
        set((state) => ({
          favorites: state.favorites.includes(id)
            ? state.favorites.filter((item) => item !== id)
            : [id, ...state.favorites],
          byUser: {
            ...state.byUser,
            [state.userId]: {
              favorites: state.favorites.includes(id)
                ? state.favorites.filter((item) => item !== id)
                : [id, ...state.favorites],
              history: state.history
            }
          }
        })),
      pushHistory: (id) =>
        set((state) => {
          const history = [id, ...state.history.filter((item) => item !== id)].slice(0, 80);
          return {
            history,
            byUser: {
              ...state.byUser,
              [state.userId]: { favorites: state.favorites, history }
            }
          };
        })
    }),
    { name: `gospel-library-state:${DEFAULT_STUDY_USER_ID}` }
  )
);

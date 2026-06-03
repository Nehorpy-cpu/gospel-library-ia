"use client";

import { create } from "zustand";

const DEFAULT_STUDY_USER_ID =
  process.env.NEXT_PUBLIC_STUDY_USER_ID ?? "00000000-0000-4000-8000-000000000001";

type StudyWorkspaceState = {
  userId: string;
  activeWorkspaceId?: string;
  activeDocumentId?: string;
  selectedText: string;
  sourceType?: string;
  topic?: string;
  scriptureRef?: string;
  setUserId: (userId: string) => void;
  setActiveWorkspaceId: (workspaceId?: string) => void;
  setActiveDocumentId: (documentId?: string) => void;
  setSelectedText: (selectedText: string) => void;
  setSourceType: (sourceType?: string) => void;
  setTopic: (topic?: string) => void;
  setScriptureRef: (scriptureRef?: string) => void;
};

export const useStudyWorkspaceStore = create<StudyWorkspaceState>((set) => ({
  userId: DEFAULT_STUDY_USER_ID,
  activeWorkspaceId: undefined,
  activeDocumentId: undefined,
  selectedText: "",
  sourceType: undefined,
  topic: undefined,
  scriptureRef: undefined,
  setUserId: (userId) => set({ userId }),
  setActiveWorkspaceId: (activeWorkspaceId) => set({ activeWorkspaceId }),
  setActiveDocumentId: (activeDocumentId) => set({ activeDocumentId }),
  setSelectedText: (selectedText) => set({ selectedText }),
  setSourceType: (sourceType) => set({ sourceType: sourceType || undefined }),
  setTopic: (topic) => set({ topic: topic || undefined }),
  setScriptureRef: (scriptureRef) => set({ scriptureRef: scriptureRef || undefined })
}));

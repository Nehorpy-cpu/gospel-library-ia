"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { ragApi } from "@/lib/api";
import type { ChatRequest, SearchRequest } from "@/types/rag";

export function useSearch(request: SearchRequest, enabled = true) {
  return useQuery({
    queryKey: ["search", request],
    queryFn: () => ragApi.search(request),
    enabled: enabled && request.query.trim().length > 0,
    staleTime: 1000 * 60
  });
}

export function useChatMutation() {
  return useMutation({
    mutationFn: (request: ChatRequest) => ragApi.chat(request)
  });
}

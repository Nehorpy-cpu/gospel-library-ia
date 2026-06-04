"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkPlus, Check, Loader2, StickyNote } from "lucide-react";

import { Button } from "@/components/ui/button";
import { studyApi } from "@/lib/api";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";

type SaveQuoteInput = {
  documentId: string;
  quote: string;
  selectedText?: string;
  citationUrl?: string;
  location?: Record<string, unknown>;
};

type Props = {
  quote: SaveQuoteInput;
  postIt?: {
    documentId?: string;
    content: string;
    color?: string;
    position?: Record<string, unknown>;
  };
  compact?: boolean;
};

export function SaveToStudyActions({ quote, postIt, compact = false }: Props) {
  const queryClient = useQueryClient();
  const { userId, activeWorkspaceId, lastSavedWorkspaceId, setActiveWorkspaceId, setLastSavedWorkspaceId } =
    useStudyWorkspaceStore();
  const [message, setMessage] = useState("");

  const workspaces = useQuery({
    queryKey: ["study-workspaces", userId],
    queryFn: () => studyApi.workspaces(userId),
    staleTime: 1000 * 30
  });

  const createWorkspace = useMutation({
    mutationFn: () => studyApi.createWorkspace(userId, { name: "Mi estudio" }),
    onSuccess: (workspace) => {
      setActiveWorkspaceId(workspace.id);
      setLastSavedWorkspaceId(workspace.id);
      queryClient.invalidateQueries({ queryKey: ["study-workspaces"] });
    }
  });

  async function ensureWorkspace() {
    const existing = activeWorkspaceId ?? lastSavedWorkspaceId ?? workspaces.data?.items[0]?.id;
    if (existing) {
      setActiveWorkspaceId(existing);
      setLastSavedWorkspaceId(existing);
      return existing;
    }
    const workspace = await createWorkspace.mutateAsync();
    return workspace.id;
  }

  const saveCitation = useMutation({
    mutationFn: async () => {
      const workspaceId = await ensureWorkspace();
      return studyApi.saveCitation(userId, workspaceId, {
        documentId: quote.documentId,
        quote: quote.quote,
        selectedText: quote.selectedText ?? quote.quote,
        citationUrl: quote.citationUrl,
        location: quote.location
      });
    },
    onMutate: () => setMessage("Guardando cita..."),
    onSuccess: (_saved, _vars, _ctx) => {
      setMessage("Cita guardada");
      queryClient.invalidateQueries({ queryKey: ["study-citations"] });
      queryClient.invalidateQueries({ queryKey: ["study-workspaces"] });
    },
    onError: () => setMessage("No se pudo guardar")
  });

  const createPostIt = useMutation({
    mutationFn: async () => {
      const workspaceId = await ensureWorkspace();
      return studyApi.createPostIt(userId, workspaceId, {
        documentId: postIt?.documentId ?? quote.documentId,
        content: postIt?.content ?? quote.quote,
        color: postIt?.color ?? "yellow",
        position: postIt?.position ?? { x: 24, y: 24 },
        pinned: true,
        sourceFilters: { savedFrom: quote.location?.source ?? "study_action" }
      });
    },
    onMutate: () => setMessage("Creando post-it..."),
    onSuccess: () => {
      setMessage("Post-it creado");
      queryClient.invalidateQueries({ queryKey: ["study-post-its"] });
      queryClient.invalidateQueries({ queryKey: ["study-workspaces"] });
    },
    onError: () => setMessage("No se pudo crear")
  });

  const disabled = !quote.documentId || !quote.quote.trim() || saveCitation.isPending || createPostIt.isPending;

  return (
    <div className="space-y-2">
      <div className={compact ? "flex gap-2" : "grid gap-2 sm:grid-cols-2"}>
        <Button size={compact ? "sm" : "default"} variant="secondary" disabled={disabled} onClick={() => saveCitation.mutate()}>
          {saveCitation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookmarkPlus className="h-4 w-4" />}
          Guardar cita
        </Button>
        <Button size={compact ? "sm" : "default"} variant="outline" disabled={disabled} onClick={() => createPostIt.mutate()}>
          {createPostIt.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <StickyNote className="h-4 w-4" />}
          Post-it
        </Button>
      </div>
      {message ? (
        <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          {message.includes("guardada") || message.includes("creado") ? <Check className="h-3 w-3 text-primary" /> : null}
          {message}
        </p>
      ) : null}
    </div>
  );
}

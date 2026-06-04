"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  BookmarkPlus,
  FileText,
  Highlighter,
  NotebookPen,
  Plus,
  RefreshCw,
  Save,
  Search,
  SlidersHorizontal,
  StickyNote,
  Trash2
} from "lucide-react";

import { CitationCard } from "@/components/search/citation-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ragApi, studyApi } from "@/lib/api";
import { mergeSourceOptions } from "@/lib/source-filters";
import { cn, truncate } from "@/lib/utils";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import type { Citation } from "@/types/rag";
import type { SavedStudyCitation, StudyDocument, StudyNote, StudyPostIt } from "@/types/study";

type Props = {
  workspaceId?: string;
};

type DraftState = {
  workspaceName: string;
  noteTitle: string;
  noteContent: string;
  citationText: string;
  postItContent: string;
  postItColor: string;
  sourceKey: string;
  language: string;
  topic: string;
  scriptureRef: string;
  documentSearch: string;
};

const initialDraft: DraftState = {
  workspaceName: "",
  noteTitle: "",
  noteContent: "",
  citationText: "",
  postItContent: "",
  postItColor: "yellow",
  sourceKey: "",
  language: "",
  topic: "",
  scriptureRef: "",
  documentSearch: ""
};

function toCitationCardItem(item: SavedStudyCitation): Citation {
  return {
    citation_id: 0,
    chunk_id: item.chunkId ?? item.id,
    document_id: item.documentId,
    title: item.sourceTitle ?? "Fuente doctrinal",
    author: item.sourceAuthor,
    source_key: item.sourceType ?? item.sourceName ?? "study",
    canonical_url: item.citationUrl ?? item.sourceUrl,
    language: null,
    section_title: null,
    quote: item.quote,
    score: 1
  };
}

export function StudyWorkspaceExperience({ workspaceId: routeWorkspaceId }: Props) {
  const queryClient = useQueryClient();
  const {
    userId,
    activeWorkspaceId,
    activeDocumentId,
    selectedText,
    sourceType,
    topic,
    scriptureRef,
    setActiveWorkspaceId,
    setActiveDocumentId,
    setSelectedText,
    setSourceType,
    setTopic,
    setScriptureRef
  } = useStudyWorkspaceStore();
  const [draft, setDraft] = useState<DraftState>(initialDraft);
  const [editingNote, setEditingNote] = useState<{ id: string; title: string; content: string } | null>(null);

  const filters = useMemo(
    () => ({
      documentId: activeDocumentId,
      sourceType,
      topic,
      scriptureRef
    }),
    [activeDocumentId, sourceType, topic, scriptureRef]
  );

  const workspaces = useQuery({
    queryKey: ["study-workspaces", userId, sourceType, topic],
    queryFn: () => studyApi.workspaces(userId, { sourceType, topic })
  });
  const sources = useQuery({ queryKey: ["source-options"], queryFn: () => ragApi.sourcesSummary(), staleTime: 1000 * 60 });

  const documents = useQuery({
    queryKey: ["study-documents", draft.documentSearch, sourceType],
    queryFn: () => ragApi.documents({ search: draft.documentSearch || undefined, sourceType, limit: 20, offset: 0 }),
    staleTime: 1000 * 60
  });

  const workspaceId = routeWorkspaceId ?? activeWorkspaceId ?? workspaces.data?.items[0]?.id;
  const activeWorkspace = workspaces.data?.items.find((item) => item.id === workspaceId);
  const activeDocument = documents.data?.items.find((item) => item.id === activeDocumentId) ?? documents.data?.items[0];

  useEffect(() => {
    if (routeWorkspaceId) {
      setActiveWorkspaceId(routeWorkspaceId);
    } else if (!activeWorkspaceId && workspaces.data?.items[0]) {
      setActiveWorkspaceId(workspaces.data.items[0].id);
    }
  }, [activeWorkspaceId, routeWorkspaceId, setActiveWorkspaceId, workspaces.data?.items]);

  useEffect(() => {
    if (!activeDocumentId && activeDocument?.id) {
      setActiveDocumentId(activeDocument.id);
    }
  }, [activeDocument?.id, activeDocumentId, setActiveDocumentId]);

  const notes = useQuery({
    queryKey: ["study-notes", userId, workspaceId, filters],
    queryFn: () => studyApi.notes(userId, workspaceId as string, filters),
    enabled: Boolean(workspaceId)
  });
  const citations = useQuery({
    queryKey: ["study-citations", userId, workspaceId, filters],
    queryFn: () => studyApi.citations(userId, workspaceId as string, filters),
    enabled: Boolean(workspaceId)
  });
  const postIts = useQuery({
    queryKey: ["study-post-its", userId, workspaceId, filters],
    queryFn: () => studyApi.postIts(userId, workspaceId as string, filters),
    enabled: Boolean(workspaceId)
  });
  const highlights = useQuery({
    queryKey: ["study-highlights", userId, workspaceId, filters],
    queryFn: () => studyApi.highlights(userId, workspaceId as string, filters),
    enabled: Boolean(workspaceId)
  });
  const sourceFilters = useQuery({
    queryKey: ["study-source-filters", userId, workspaceId],
    queryFn: () => studyApi.sourceFilters(userId, workspaceId as string),
    enabled: Boolean(workspaceId)
  });

  const invalidateWorkspace = () => {
    queryClient.invalidateQueries({ queryKey: ["study-workspaces"] });
    queryClient.invalidateQueries({ queryKey: ["study-notes"] });
    queryClient.invalidateQueries({ queryKey: ["study-citations"] });
    queryClient.invalidateQueries({ queryKey: ["study-post-its"] });
    queryClient.invalidateQueries({ queryKey: ["study-highlights"] });
    queryClient.invalidateQueries({ queryKey: ["study-source-filters"] });
  };

  const createWorkspace = useMutation({
    mutationFn: () => studyApi.createWorkspace(userId, { name: draft.workspaceName.trim() }),
    onSuccess: (workspace) => {
      setDraft((value) => ({ ...value, workspaceName: "" }));
      setActiveWorkspaceId(workspace.id);
      invalidateWorkspace();
    }
  });

  const createNote = useMutation({
    mutationFn: () =>
      studyApi.createNote(userId, workspaceId as string, {
        documentId: activeDocumentId,
        title: draft.noteTitle.trim() || activeDocument?.title,
        content: draft.noteContent.trim(),
        selectedText: selectedText || undefined,
        scriptureRefs: scriptureRef ? [scriptureRef] : []
      }),
    onSuccess: () => {
      setDraft((value) => ({ ...value, noteTitle: "", noteContent: "" }));
      setSelectedText("");
      invalidateWorkspace();
    }
  });

  const updateNote = useMutation({
    mutationFn: (note: { id: string; title: string; content: string }) =>
      studyApi.updateNote(userId, workspaceId as string, note.id, {
        title: note.title.trim(),
        content: note.content.trim()
      }),
    onSuccess: () => {
      setEditingNote(null);
      invalidateWorkspace();
    }
  });

  const deleteNote = useMutation({
    mutationFn: (noteId: string) => studyApi.deleteNote(userId, workspaceId as string, noteId),
    onSuccess: invalidateWorkspace
  });

  const saveCitation = useMutation({
    mutationFn: () =>
      studyApi.saveCitation(userId, workspaceId as string, {
        documentId: activeDocumentId as string,
        quote: (draft.citationText || selectedText).trim(),
        selectedText: selectedText || undefined,
        citationUrl: activeDocument?.url ?? undefined,
        scriptureRefs: scriptureRef ? [scriptureRef] : []
      }),
    onSuccess: () => {
      setDraft((value) => ({ ...value, citationText: "" }));
      setSelectedText("");
      invalidateWorkspace();
    }
  });

  const createHighlight = useMutation({
    mutationFn: () =>
      studyApi.createHighlight(userId, workspaceId as string, {
        documentId: activeDocumentId as string,
        startChar: 0,
        endChar: selectedText.length,
        selectedText,
        scriptureRefs: scriptureRef ? [scriptureRef] : []
      }),
    onSuccess: () => {
      setSelectedText("");
      invalidateWorkspace();
    }
  });

  const createPostIt = useMutation({
    mutationFn: () =>
      studyApi.createPostIt(userId, workspaceId as string, {
        documentId: activeDocumentId,
        content: draft.postItContent.trim(),
        color: draft.postItColor,
        position: { x: 24, y: 24 },
        pinned: true,
        sourceFilters: { sourceType, topic, scriptureRef }
      }),
    onSuccess: () => {
      setDraft((value) => ({ ...value, postItContent: "" }));
      invalidateWorkspace();
    }
  });

  const updatePostIt = useMutation({
    mutationFn: ({
      postItId,
      patch
    }: {
      postItId: string;
      patch: { content?: string; color?: string; position?: Record<string, unknown>; pinned?: boolean };
    }) => studyApi.updatePostIt(userId, workspaceId as string, postItId, patch),
    onMutate: async ({ postItId, patch }) => {
      const queryKey = ["study-post-its", userId, workspaceId, filters];
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<{ items: StudyPostIt[] }>(queryKey);
      if (previous) {
        queryClient.setQueryData<{ items: StudyPostIt[] }>(queryKey, {
          items: previous.items.map((item) => (item.id === postItId ? { ...item, ...patch } : item))
        });
      }
      return { previous, queryKey };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(context.queryKey, context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["study-post-its"] })
  });

  const createSourceFilter = useMutation({
    mutationFn: () =>
      studyApi.createSourceFilter(userId, workspaceId as string, {
        sourceKey: draft.sourceKey.trim() || undefined,
        language: draft.language.trim() || undefined,
        category: topic || undefined,
        tags: scriptureRef ? [scriptureRef] : []
      }),
    onSuccess: () => {
      setDraft((value) => ({ ...value, sourceKey: "", language: "" }));
      invalidateWorkspace();
    }
  });

  const deleteSourceFilter = useMutation({
    mutationFn: (sourceFilterId: string) => studyApi.deleteSourceFilter(userId, workspaceId as string, sourceFilterId),
    onSuccess: invalidateWorkspace
  });

  const deleteCitation = useMutation({
    mutationFn: (citationId: string) => studyApi.deleteCitation(userId, workspaceId as string, citationId),
    onSuccess: invalidateWorkspace
  });

  const deletePostIt = useMutation({
    mutationFn: (postItId: string) => studyApi.deletePostIt(userId, workspaceId as string, postItId),
    onSuccess: invalidateWorkspace
  });

  const deleteHighlight = useMutation({
    mutationFn: (highlightId: string) => studyApi.deleteHighlight(userId, workspaceId as string, highlightId),
    onSuccess: invalidateWorkspace
  });

  const applySelection = () => {
    const selection = window.getSelection()?.toString().trim();
    if (selection) {
      setSelectedText(selection);
      if (!draft.noteContent) {
        setDraft((value) => ({ ...value, noteContent: selection }));
      }
    }
  };

  const canCreateWorkspace = draft.workspaceName.trim().length > 0;
  const canCreateNote = Boolean(workspaceId && draft.noteContent.trim());
  const canSaveCitation = Boolean(workspaceId && activeDocumentId && (draft.citationText.trim() || selectedText));
  const canHighlight = Boolean(workspaceId && activeDocumentId && selectedText);
  const canPostIt = Boolean(workspaceId && draft.postItContent.trim());
  const canSourceFilter = Boolean(workspaceId && (draft.sourceKey.trim() || draft.language.trim() || topic || scriptureRef));

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">StudyWorkspace</p>
          <h1 className="text-2xl font-semibold">Espacio de estudio doctrinal</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Organiza notas, citas, subrayados y filtros sobre documentos reales cargados en Gospel Library IA.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => invalidateWorkspace()}>
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </Button>
          {activeDocumentId ? (
            <Link href={`/documents/${activeDocumentId}`}>
              <Button variant="secondary">
                <BookOpen className="h-4 w-4" />
                Abrir lector
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <section className="grid gap-4 xl:grid-cols-[280px_1fr_360px]">
        <aside className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <NotebookPen className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Workspaces</h2>
            </div>
            <div className="mt-4 flex gap-2">
              <Input
                value={draft.workspaceName}
                onChange={(event) => setDraft((value) => ({ ...value, workspaceName: event.target.value }))}
                placeholder="Nuevo workspace"
              />
              <Button size="icon" disabled={!canCreateWorkspace || createWorkspace.isPending} onClick={() => createWorkspace.mutate()}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="mt-4 space-y-2">
              {workspaces.isLoading ? <p className="text-sm text-muted-foreground">Cargando espacios...</p> : null}
              {workspaces.data?.items.map((workspace) => (
                <Link
                  key={workspace.id}
                  href={`/study/${workspace.id}`}
                  onClick={() => setActiveWorkspaceId(workspace.id)}
                  className={cn(
                    "block rounded-md border px-3 py-2 text-sm transition hover:bg-muted",
                    workspace.id === workspaceId && "border-primary bg-primary/10 text-primary"
                  )}
                >
                  <span className="block font-medium">{workspace.name}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {workspace.updatedAt ? new Date(workspace.updatedAt).toLocaleDateString() : "Sin actividad"}
                  </span>
                </Link>
              ))}
              {!workspaces.isLoading && workspaces.data?.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">Crea un workspace para empezar.</p>
              ) : null}
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Filtros</h2>
            </div>
            <div className="mt-4 space-y-3">
              <select
                value={sourceType ?? ""}
                onChange={(event) => setSourceType(event.target.value)}
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                aria-label="Tipo de fuente"
              >
                <option value="">Todas las fuentes</option>
                {mergeSourceOptions(sources.data?.items).map((source) => (
                  <option key={source.key} value={source.key}>
                    {source.label}
                    {typeof source.documentCount === "number" ? ` (${source.documentCount})` : ""}
                  </option>
                ))}
              </select>
              <Input value={topic ?? ""} onChange={(event) => setTopic(event.target.value)} placeholder="Tema" />
              <Input
                value={scriptureRef ?? ""}
                onChange={(event) => setScriptureRef(event.target.value)}
                placeholder="Referencia escritural"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={draft.sourceKey}
                  onChange={(event) => setDraft((value) => ({ ...value, sourceKey: event.target.value }))}
                  className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                  aria-label="Fuente guardada"
                >
                  <option value="">Fuente</option>
                  {mergeSourceOptions(sources.data?.items).map((source) => (
                    <option key={source.key} value={source.key}>
                      {source.label}
                    </option>
                  ))}
                </select>
                <Input
                  value={draft.language}
                  onChange={(event) => setDraft((value) => ({ ...value, language: event.target.value }))}
                  placeholder="Idioma"
                />
              </div>
              <Button
                className="w-full"
                variant="outline"
                disabled={!canSourceFilter || createSourceFilter.isPending}
                onClick={() => createSourceFilter.mutate()}
              >
                <Save className="h-4 w-4" />
                Guardar filtro
              </Button>
              <div className="flex flex-wrap gap-2">
                {sourceFilters.data?.items.map((filter) => (
                  <button
                    key={filter.id}
                    onClick={() => deleteSourceFilter.mutate(filter.id)}
                    className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                  >
                    {filter.sourceKey ?? filter.language ?? filter.category ?? "Filtro"}
                    <Trash2 className="h-3 w-3" />
                  </button>
                ))}
              </div>
            </div>
          </Card>
        </aside>

        <main className="space-y-4">
          <Card className="p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="font-semibold">{activeWorkspace?.name ?? "Workspace sin seleccionar"}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {notes.data?.items.length ?? 0} notas, {citations.data?.items.length ?? 0} citas,{" "}
                  {highlights.data?.items.length ?? 0} subrayados.
                </p>
              </div>
              <div className="relative md:w-80">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={draft.documentSearch}
                  onChange={(event) => setDraft((value) => ({ ...value, documentSearch: event.target.value }))}
                  placeholder="Buscar documento real"
                />
              </div>
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
            <Card className="max-h-[520px] overflow-auto p-3">
              <h3 className="px-1 text-sm font-semibold">Documentos</h3>
              <div className="mt-3 space-y-2">
                {documents.data?.items.map((document) => (
                  <DocumentChoice
                    key={document.id}
                    document={document}
                    active={document.id === activeDocumentId}
                    onClick={() => setActiveDocumentId(document.id)}
                  />
                ))}
                {documents.isLoading ? <p className="px-1 text-sm text-muted-foreground">Cargando documentos...</p> : null}
                {!documents.isLoading && documents.data?.items.length === 0 ? (
                  <p className="px-1 text-sm text-muted-foreground">No hay documentos para este filtro.</p>
                ) : null}
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold">{activeDocument?.title ?? "Documento no seleccionado"}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {activeDocument?.author ?? "Autor desconocido"} · {activeDocument?.sourceType ?? activeDocument?.source ?? "Fuente"}
                  </p>
                </div>
                {activeDocument?.status ? <Badge>{activeDocument.status}</Badge> : null}
              </div>
              <div
                onMouseUp={applySelection}
                className="mt-4 max-h-[360px] overflow-auto rounded-md border bg-muted/30 p-4 text-sm leading-7 text-muted-foreground"
              >
                {activeDocument?.excerpt ? (
                  activeDocument.excerpt
                ) : (
                  <span>Selecciona un documento con extracto para crear notas y citas desde contenido real.</span>
                )}
              </div>
              {selectedText ? (
                <div className="mt-3 rounded-md border border-primary/30 bg-primary/10 p-3 text-sm">
                  <p className="font-medium text-primary">Seleccion activa</p>
                  <p className="mt-1 text-muted-foreground">{truncate(selectedText, 260)}</p>
                </div>
              ) : null}
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Input
                    value={draft.noteTitle}
                    onChange={(event) => setDraft((value) => ({ ...value, noteTitle: event.target.value }))}
                    placeholder="Titulo de nota"
                  />
                  <textarea
                    value={draft.noteContent}
                    onChange={(event) => setDraft((value) => ({ ...value, noteContent: event.target.value }))}
                    placeholder="Nota personal"
                    className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                  />
                  <Button className="w-full" disabled={!canCreateNote || createNote.isPending} onClick={() => createNote.mutate()}>
                    <NotebookPen className="h-4 w-4" />
                    Crear nota
                  </Button>
                </div>
                <div className="space-y-2">
                  <textarea
                    value={draft.citationText || selectedText}
                    onChange={(event) => setDraft((value) => ({ ...value, citationText: event.target.value }))}
                    placeholder="Cita guardada"
                    className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="secondary" disabled={!canSaveCitation || saveCitation.isPending} onClick={() => saveCitation.mutate()}>
                      <BookmarkPlus className="h-4 w-4" />
                      Cita
                    </Button>
                    <Button variant="outline" disabled={!canHighlight || createHighlight.isPending} onClick={() => createHighlight.mutate()}>
                      <Highlighter className="h-4 w-4" />
                      Subrayar
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          <StudyNotesPanel
            notes={notes.data?.items ?? []}
            editingNote={editingNote}
            onEdit={setEditingNote}
            onUpdate={(note) => updateNote.mutate(note)}
            onDelete={(noteId) => deleteNote.mutate(noteId)}
          />
        </main>

        <aside className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <BookmarkPlus className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Citas guardadas</h2>
            </div>
            <div className="mt-4 space-y-3">
              {citations.data?.items.map((citation) => (
                <div key={citation.id} className="space-y-2">
                  <CitationCard item={toCitationCardItem(citation)} />
                  <Button variant="ghost" size="sm" onClick={() => deleteCitation.mutate(citation.id)}>
                    <Trash2 className="h-4 w-4" />
                    Eliminar cita
                  </Button>
                </div>
              ))}
              {citations.data?.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">Selecciona texto de un documento para guardar una cita con fuente.</p>
              ) : null}
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2">
              <StickyNote className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Post-it</h2>
            </div>
            <textarea
              value={draft.postItContent}
              onChange={(event) => setDraft((value) => ({ ...value, postItContent: event.target.value }))}
              placeholder="Idea rapida"
              className="mt-4 min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <div className="mt-2 flex gap-2">
              {["yellow", "blue", "green", "rose"].map((color) => (
                <button
                  key={color}
                  onClick={() => setDraft((value) => ({ ...value, postItColor: color }))}
                  className={cn(
                    "h-7 w-7 rounded-md border",
                    color === "yellow" && "bg-yellow-300",
                    color === "blue" && "bg-sky-300",
                    color === "green" && "bg-emerald-300",
                    color === "rose" && "bg-rose-300",
                    draft.postItColor === color && "ring-2 ring-primary"
                  )}
                  aria-label={`Color ${color}`}
                />
              ))}
            </div>
            <Button className="mt-2 w-full" variant="outline" disabled={!canPostIt || createPostIt.isPending} onClick={() => createPostIt.mutate()}>
              <Plus className="h-4 w-4" />
              Agregar post-it
            </Button>
            <div className="mt-4 space-y-2">
              {postIts.data?.items.map((postIt) => (
                <PostItCard
                  key={postIt.id}
                  postIt={postIt}
                  onDelete={() => deletePostIt.mutate(postIt.id)}
                  onUpdate={(patch) => updatePostIt.mutate({ postItId: postIt.id, patch })}
                />
              ))}
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2">
              <Highlighter className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Subrayados</h2>
            </div>
            <div className="mt-4 space-y-2">
              {highlights.data?.items.map((highlight) => (
                <div key={highlight.id} className="rounded-md border p-3 text-sm">
                  <p className="text-muted-foreground">{truncate(highlight.selectedText, 180)}</p>
                  <button onClick={() => deleteHighlight.mutate(highlight.id)} className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                    <Trash2 className="h-3 w-3" />
                    Eliminar
                  </button>
                </div>
              ))}
              {highlights.data?.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aun no hay subrayados para estos filtros.</p>
              ) : null}
            </div>
          </Card>
        </aside>
      </section>
    </div>
  );
}

function DocumentChoice({ document, active, onClick }: { document: StudyDocument; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-md border p-3 text-left text-sm transition hover:bg-muted",
        active && "border-primary bg-primary/10"
      )}
    >
      <span className="flex items-start gap-2">
        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <span>
          <span className="line-clamp-2 font-medium">{document.title}</span>
          <span className="mt-1 block text-xs text-muted-foreground">
            {document.author ?? "Autor desconocido"} · {document.sourceType ?? document.source ?? "Fuente"}
          </span>
        </span>
      </span>
    </button>
  );
}

function postItColorClass(color: string) {
  if (color === "blue") return "border-sky-300 bg-sky-100 text-sky-950 dark:bg-sky-950/40 dark:text-sky-100";
  if (color === "green") return "border-emerald-300 bg-emerald-100 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100";
  if (color === "rose") return "border-rose-300 bg-rose-100 text-rose-950 dark:bg-rose-950/40 dark:text-rose-100";
  return "border-yellow-300 bg-yellow-100 text-yellow-950 dark:bg-yellow-950/40 dark:text-yellow-100";
}

function PostItCard({
  postIt,
  onDelete,
  onUpdate
}: {
  postIt: StudyPostIt;
  onDelete: () => void;
  onUpdate: (patch: { content?: string; color?: string; position?: Record<string, unknown>; pinned?: boolean }) => void;
}) {
  const x = typeof postIt.position?.x === "number" ? postIt.position.x : 24;
  const y = typeof postIt.position?.y === "number" ? postIt.position.y : 24;
  const move = (dx: number, dy: number) => onUpdate({ position: { ...postIt.position, x: x + dx, y: y + dy } });

  return (
    <div className={cn("rounded-md border p-3 text-sm", postItColorClass(postIt.color))}>
      <textarea
        defaultValue={postIt.content}
        onBlur={(event) => {
          const next = event.target.value.trim();
          if (next && next !== postIt.content) onUpdate({ content: next });
        }}
        className="min-h-20 w-full resize-none rounded-md border border-black/10 bg-white/50 px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-ring dark:bg-black/20"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {["yellow", "blue", "green", "rose"].map((color) => (
          <button
            key={color}
            onClick={() => onUpdate({ color })}
            className={cn(
              "h-6 w-6 rounded-md border border-black/10",
              color === "yellow" && "bg-yellow-300",
              color === "blue" && "bg-sky-300",
              color === "green" && "bg-emerald-300",
              color === "rose" && "bg-rose-300",
              postIt.color === color && "ring-2 ring-primary"
            )}
            aria-label={`Cambiar a ${color}`}
          />
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="grid grid-cols-3 gap-1">
          <span />
          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => move(0, -16)} aria-label="Mover arriba">
            <ArrowUp className="h-3.5 w-3.5" />
          </Button>
          <span />
          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => move(-16, 0)} aria-label="Mover izquierda">
            <ArrowLeft className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => move(0, 16)} aria-label="Mover abajo">
            <ArrowDown className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => move(16, 0)} aria-label="Mover derecha">
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
        <button onClick={onDelete} className="inline-flex items-center gap-1 text-xs opacity-80 hover:opacity-100">
          <Trash2 className="h-3 w-3" />
          Eliminar
        </button>
      </div>
      <p className="mt-2 text-xs opacity-70">
        Posicion {x}, {y}
      </p>
    </div>
  );
}

function StudyNotesPanel({
  notes,
  editingNote,
  onEdit,
  onUpdate,
  onDelete
}: {
  notes: StudyNote[];
  editingNote: { id: string; title: string; content: string } | null;
  onEdit: (note: { id: string; title: string; content: string } | null) => void;
  onUpdate: (note: { id: string; title: string; content: string }) => void;
  onDelete: (noteId: string) => void;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2">
        <NotebookPen className="h-4 w-4 text-primary" />
        <h2 className="font-semibold">Notas</h2>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {notes.map((note) => {
          const editing = editingNote?.id === note.id;
          return (
            <div key={note.id} className="rounded-md border p-3">
              {editing ? (
                <div className="space-y-2">
                  <Input
                    value={editingNote.title}
                    onChange={(event) => onEdit({ ...editingNote, title: event.target.value })}
                    placeholder="Titulo"
                  />
                  <textarea
                    value={editingNote.content}
                    onChange={(event) => onEdit({ ...editingNote, content: event.target.value })}
                    className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => onUpdate(editingNote)}>
                      <Save className="h-4 w-4" />
                      Guardar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => onEdit(null)}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <h3 className="font-medium">{note.title ?? "Nota sin titulo"}</h3>
                  {note.selectedText ? (
                    <p className="mt-2 rounded-md bg-muted p-2 text-xs text-muted-foreground">{truncate(note.selectedText, 160)}</p>
                  ) : null}
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{note.content}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {note.scriptureRefs.map((ref) => (
                      <Badge key={ref}>{ref}</Badge>
                    ))}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => onEdit({ id: note.id, title: note.title ?? "", content: note.content })}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => onDelete(note.id)}>
                      <Trash2 className="h-4 w-4" />
                      Eliminar
                    </Button>
                  </div>
                </>
              )}
            </div>
          );
        })}
        {notes.length === 0 ? <p className="text-sm text-muted-foreground">No hay notas para este workspace y filtros.</p> : null}
      </div>
    </Card>
  );
}

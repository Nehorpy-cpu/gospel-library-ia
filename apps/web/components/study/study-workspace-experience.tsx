"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Download, Plus, Save, Sparkles, StickyNote, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { studyApi } from "@/lib/api";
import {
  type EditableWorkspaceAiSuggestion,
  isSuggestedReference,
  mapWorkspaceAiTypeToBlockType,
  sourceStatusLabel
} from "@/lib/study-ai";
import { cn } from "@/lib/utils";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import type { StudyBlock, StudyBlockType, StudyWorkspace, WorkspaceAiSuggestionMode } from "@/types/study";

type Props = {
  workspaceId?: string;
};

type AiFormState = {
  mode: WorkspaceAiSuggestionMode;
  userPrompt: string;
  maxSuggestions: number;
};

const blockLabels: Record<string, string> = {
  personal_note: "Nota personal",
  post_it: "Post-it",
  scripture: "Escritura",
  quote: "Cita manual",
  reflection: "Reflexion",
  doctrinal_analysis: "Analisis doctrinal"
};

const aiModeLabels: Record<WorkspaceAiSuggestionMode, string> = {
  rapido: "Rapido",
  profundo: "Profundo",
  citas: "Citas",
  manuales: "Manuales",
  nombres: "Nombres",
  llamamiento: "Llamamiento"
};

const aiTypeLabels: Record<EditableWorkspaceAiSuggestion["type"], string> = {
  doctrinal_analysis: "Analisis doctrinal",
  scripture_context: "Contexto de escritura",
  name_meaning: "Significado de nombres",
  christ_connection: "Relacion con Jesucristo",
  scripture_connection: "Conexion de escrituras",
  quote: "Cita",
  manual_reference: "Referencia de manual",
  book_reference: "Referencia de libro",
  calling_application: "Aplicacion al llamamiento",
  reflection_question: "Pregunta de reflexion",
  powerful_phrase: "Frase poderosa",
  personal_application: "Aplicacion personal"
};

const confidenceLabels: Record<EditableWorkspaceAiSuggestion["confidence"], string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta"
};

export function StudyWorkspaceExperience({ workspaceId: routeWorkspaceId }: Props) {
  const queryClient = useQueryClient();
  const userId = useStudyWorkspaceStore((state) => state.userId);
  const [manualBlock, setManualBlock] = useState({ title: "", content: "", quoteText: "" });
  const [postIt, setPostIt] = useState("");
  const [reflection, setReflection] = useState("");
  const [editingBlock, setEditingBlock] = useState<StudyBlock | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiForm, setAiForm] = useState<AiFormState>({
    mode: "rapido" as WorkspaceAiSuggestionMode,
    userPrompt: "",
    maxSuggestions: 8
  });
  const [aiSuggestions, setAiSuggestions] = useState<EditableWorkspaceAiSuggestion[]>([]);
  const [aiWarnings, setAiWarnings] = useState<string[]>([]);
  const [aiStatus, setAiStatus] = useState<string | null>(null);

  const workspaces = useQuery({
    queryKey: ["study-workspaces", userId],
    queryFn: () => studyApi.workspaces(userId)
  });

  const workspaceId = routeWorkspaceId ?? workspaces.data?.items[0]?.id;
  const workspace = useQuery({
    queryKey: ["study-workspace", userId, workspaceId],
    queryFn: () => studyApi.workspace(userId, workspaceId as string),
    enabled: Boolean(workspaceId)
  });

  const activeWorkspace = workspace.data;
  const blocks = useMemo(() => activeWorkspace?.blocks ?? [], [activeWorkspace?.blocks]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["study-workspaces"] });
    queryClient.invalidateQueries({ queryKey: ["study-workspace", userId, workspaceId] });
  };

  const createBlock = useMutation({
    mutationFn: (payload: {
      type: StudyBlockType;
      title: string;
      content?: string;
      quoteText?: string | null;
      sourceTitle?: string | null;
      sourceAuthor?: string | null;
      sourceReference?: string | null;
      sourceUrl?: string | null;
      isAiGenerated?: boolean;
    }) => studyApi.createWorkspaceBlock(userId, workspaceId as string, payload),
    onSuccess: () => {
      setManualBlock({ title: "", content: "", quoteText: "" });
      setPostIt("");
      setReflection("");
      invalidate();
    }
  });

  const updateBlock = useMutation({
    mutationFn: (block: Partial<StudyBlock> & { id: string }) =>
      studyApi.updateWorkspaceBlock(userId, workspaceId as string, block.id, block),
    onSuccess: () => {
      setEditingBlock(null);
      invalidate();
    }
  });

  const deleteBlock = useMutation({
    mutationFn: (blockId: string) => studyApi.deleteWorkspaceBlock(userId, workspaceId as string, blockId),
    onSuccess: invalidate
  });

  const archiveWorkspace = useMutation({
    mutationFn: () => studyApi.deleteWorkspace(userId, workspaceId as string),
    onSuccess: invalidate
  });

  const generateAiSuggestions = useMutation({
    mutationFn: () =>
      studyApi.suggestWorkspaceBlocks(userId, workspaceId as string, {
        mode: aiForm.mode,
        userPrompt: aiForm.userPrompt.trim() || undefined,
        preferredSources: ["biblioteca", "manuales", "discursos"],
        maxSuggestions: aiForm.maxSuggestions
      }),
    onMutate: () => {
      setAiStatus("Generando sugerencias...");
      setAiWarnings([]);
    },
    onSuccess: (response) => {
      setAiSuggestions(
        response.suggestions.map((suggestion, index) => ({
          ...suggestion,
          localId: `${Date.now()}-${index}`
        }))
      );
      setAiWarnings(response.warnings);
      setAiStatus(response.suggestions.length ? "Sugerencias generadas" : "No se encontraron suficientes fuentes locales");
    },
    onError: (error) => {
      setAiStatus(error instanceof Error ? error.message : "No se pudo generar informacion con IA");
    }
  });

  const saveAiSuggestion = useMutation({
    mutationFn: (suggestion: EditableWorkspaceAiSuggestion) =>
      studyApi.createWorkspaceBlock(userId, workspaceId as string, {
        type: mapWorkspaceAiTypeToBlockType(suggestion.type),
        title: suggestion.title,
        content: suggestion.content,
        quoteText: suggestion.quote_text,
        sourceTitle: suggestion.source_title,
        sourceAuthor: suggestion.source_author,
        sourceReference: suggestion.source_reference,
        sourceUrl: suggestion.source_url,
        isAiGenerated: true
      }),
    onSuccess: (_, suggestion) => {
      setAiSuggestions((items) => items.map((item) => (item.localId === suggestion.localId ? { ...item, saved: true } : item)));
      invalidate();
    }
  });

  const exportMarkdown = () => {
    if (!activeWorkspace) return;
    const markdown = renderStudyMarkdown(activeWorkspace, blocks);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${(activeWorkspace.title || activeWorkspace.name).toLowerCase().replace(/[^a-z0-9]+/gi, "-") || "estudio"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!workspaceId && !workspaces.isLoading) {
    return <EmptyStudyState />;
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Mesa de Estudio Doctrinal</p>
          <h1 className="text-2xl font-semibold">Mis Estudios</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Organiza tus estudios personales con notas, post-its, citas manuales y reflexiones editables.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/study/new">
            <Button>
              <Plus className="h-4 w-4" />
              Nuevo estudio
            </Button>
          </Link>
          <Button variant="outline" disabled={!activeWorkspace} onClick={exportMarkdown}>
            <Download className="h-4 w-4" />
            Exportar estudio
          </Button>
          <Button variant="ghost" disabled={!activeWorkspace || archiveWorkspace.isPending} onClick={() => archiveWorkspace.mutate()}>
            <Trash2 className="h-4 w-4" />
            Archivar
          </Button>
        </div>
      </header>

      <section className="grid gap-4 xl:grid-cols-[280px_1fr_360px]">
        <aside className="space-y-4">
          <Card className="p-4">
            <h2 className="font-semibold">Estudios</h2>
            <div className="mt-3 space-y-2">
              {workspaces.data?.items.map((item) => (
                <Link
                  key={item.id}
                  href={`/study/${item.id}`}
                  className={cn(
                    "block rounded-md border p-3 text-sm transition hover:bg-muted",
                    item.id === workspaceId && "border-primary bg-primary/10"
                  )}
                >
                  <span className="line-clamp-2 font-medium">{item.title || item.name}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {item.scriptureReference || item.topic || "Sin referencia"}
                  </span>
                </Link>
              ))}
              {workspaces.isLoading ? <p className="text-sm text-muted-foreground">Cargando estudios...</p> : null}
              {!workspaces.isLoading && !workspaces.data?.items.length ? (
                <p className="text-sm text-muted-foreground">Todavia no hay estudios guardados.</p>
              ) : null}
            </div>
          </Card>
        </aside>

        <main className="space-y-4">
          <WorkspaceSummary workspace={activeWorkspace} loading={workspace.isLoading} />
          <Card className="p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="font-semibold">Bloques del estudio</h2>
                <p className="mt-1 text-sm text-muted-foreground">Edita, guarda o elimina cualquier bloque.</p>
              </div>
              <Button variant="outline" disabled={!workspaceId} onClick={() => setAiPanelOpen((value) => !value)}>
                <Sparkles className="h-4 w-4" />
                Anadir informacion con IA
              </Button>
            </div>
            {aiPanelOpen ? (
              <AiSuggestionsPanel
                form={aiForm}
                suggestions={aiSuggestions}
                warnings={aiWarnings}
                status={aiStatus}
                generating={generateAiSuggestions.isPending}
                saving={saveAiSuggestion.isPending}
                onFormChange={setAiForm}
                onGenerate={() => generateAiSuggestions.mutate()}
                onSuggestionChange={(localId, patch) =>
                  setAiSuggestions((items) => items.map((item) => (item.localId === localId ? { ...item, ...patch } : item)))
                }
                onDiscard={(localId) => setAiSuggestions((items) => items.filter((item) => item.localId !== localId))}
                onSave={(suggestion) => saveAiSuggestion.mutate(suggestion)}
              />
            ) : null}
          </Card>

          <div className="grid gap-3">
            {blocks.map((block) => (
              <StudyBlockCard
                key={block.id}
                block={block}
                editing={editingBlock?.id === block.id ? editingBlock : null}
                onEdit={setEditingBlock}
                onSave={(next) => updateBlock.mutate(next)}
                onDelete={() => deleteBlock.mutate(block.id)}
              />
            ))}
            {!workspace.isLoading && blocks.length === 0 ? (
              <p className="rounded-md border p-4 text-sm text-muted-foreground">
                Todavia no hay bloques. Agrega una reflexion, una cita manual o un post-it.
              </p>
            ) : null}
          </div>
        </main>

        <aside className="space-y-4">
          <Card className="p-4">
            <h2 className="font-semibold">Anadir cita manual</h2>
            <div className="mt-3 space-y-2">
              <Input
                value={manualBlock.title}
                onChange={(event) => setManualBlock((value) => ({ ...value, title: event.target.value }))}
                placeholder="Fuente o titulo"
              />
              <textarea
                value={manualBlock.quoteText}
                onChange={(event) => setManualBlock((value) => ({ ...value, quoteText: event.target.value }))}
                placeholder="Cita corta"
                className="min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <textarea
                value={manualBlock.content}
                onChange={(event) => setManualBlock((value) => ({ ...value, content: event.target.value }))}
                placeholder="Comentario personal"
                className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <Button
                className="w-full"
                variant="outline"
                disabled={!workspaceId || !manualBlock.quoteText.trim() || createBlock.isPending}
                onClick={() =>
                  createBlock.mutate({
                    type: "quote",
                    title: manualBlock.title.trim() || "Cita manual",
                    quoteText: manualBlock.quoteText.trim(),
                    content: manualBlock.content.trim(),
                    sourceTitle: manualBlock.title.trim() || undefined
                  })
                }
              >
                <BookOpen className="h-4 w-4" />
                Anadir cita manual
              </Button>
            </div>
          </Card>

          <Card className="p-4">
            <h2 className="font-semibold">Anadir reflexion</h2>
            <textarea
              value={reflection}
              onChange={(event) => setReflection(event.target.value)}
              placeholder="Escribe una reflexion personal"
              className="mt-3 min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <Button
              className="mt-2 w-full"
              variant="outline"
              disabled={!workspaceId || !reflection.trim() || createBlock.isPending}
              onClick={() => createBlock.mutate({ type: "reflection", title: "Reflexion", content: reflection.trim() })}
            >
              <Plus className="h-4 w-4" />
              Anadir reflexion
            </Button>
          </Card>

          <Card className="p-4">
            <h2 className="flex items-center gap-2 font-semibold">
              <StickyNote className="h-4 w-4 text-primary" />
              Anadir post-it
            </h2>
            <textarea
              value={postIt}
              onChange={(event) => setPostIt(event.target.value)}
              placeholder="Idea rapida"
              className="mt-3 min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <Button
              className="mt-2 w-full"
              variant="outline"
              disabled={!workspaceId || !postIt.trim() || createBlock.isPending}
              onClick={() => createBlock.mutate({ type: "post_it", title: "Post-it", content: postIt.trim() })}
            >
              <Plus className="h-4 w-4" />
              Anadir post-it
            </Button>
          </Card>
        </aside>
      </section>
    </div>
  );
}

function EmptyStudyState() {
  return (
    <Card className="mx-auto max-w-2xl p-8 text-center">
      <p className="text-sm font-medium text-primary">Mesa de Estudio Doctrinal</p>
      <h1 className="mt-2 text-2xl font-semibold">Todavia no hay estudios guardados.</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Crea tu primer estudio personal con una escritura base, una impresion y bloques editables.
      </p>
      <Link href="/study/new">
        <Button className="mt-5">
          <Plus className="h-4 w-4" />
          Crear estudio
        </Button>
      </Link>
    </Card>
  );
}

function AiSuggestionsPanel({
  form,
  suggestions,
  warnings,
  status,
  generating,
  saving,
  onFormChange,
  onGenerate,
  onSuggestionChange,
  onDiscard,
  onSave
}: {
  form: AiFormState;
  suggestions: EditableWorkspaceAiSuggestion[];
  warnings: string[];
  status: string | null;
  generating: boolean;
  saving: boolean;
  onFormChange: (form: AiFormState) => void;
  onGenerate: () => void;
  onSuggestionChange: (localId: string, patch: Partial<EditableWorkspaceAiSuggestion>) => void;
  onDiscard: (localId: string) => void;
  onSave: (suggestion: EditableWorkspaceAiSuggestion) => void;
}) {
  return (
    <div className="mt-4 rounded-lg border bg-muted/20 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <div className="grid flex-1 gap-3 md:grid-cols-[180px_1fr_120px]">
          <label className="text-sm">
            <span className="mb-1 block font-medium">Modo</span>
            <select
              value={form.mode}
              onChange={(event) => onFormChange({ ...form, mode: event.target.value as WorkspaceAiSuggestionMode })}
              className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              {Object.entries(aiModeLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Pedido opcional</span>
            <Input
              value={form.userPrompt}
              onChange={(event) => onFormChange({ ...form, userPrompt: event.target.value })}
              placeholder="Ej.: conecta este pasaje con Jesucristo y mi llamamiento"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Cantidad</span>
            <Input
              type="number"
              min={1}
              max={12}
              value={form.maxSuggestions}
              onChange={(event) =>
                onFormChange({ ...form, maxSuggestions: Math.min(Math.max(Number(event.target.value) || 1, 1), 12) })
              }
            />
          </label>
        </div>
        <Button disabled={generating} onClick={onGenerate}>
          <Sparkles className="h-4 w-4" />
          {generating ? "Generando..." : "Generar sugerencias"}
        </Button>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        La IA propone bloques editables. Nada se guarda en tu estudio hasta que presiones Guardar bloque.
      </p>
      {status ? <p className="mt-3 rounded-md bg-background p-2 text-sm text-muted-foreground">{status}</p> : null}
      {warnings.length ? (
        <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/20 dark:text-amber-100">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      {suggestions.length ? (
        <div className="mt-4 grid gap-3">
          {suggestions.map((suggestion) => (
            <Card key={suggestion.localId} className={cn("p-4", suggestion.saved && "border-primary/60 bg-primary/5")}>
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="flex flex-wrap gap-2">
                  <Badge>{aiTypeLabels[suggestion.type]}</Badge>
                  <Badge>{sourceStatusLabel(suggestion.source_status)}</Badge>
                  <Badge>Confianza {confidenceLabels[suggestion.confidence]}</Badge>
                  {suggestion.saved ? <Badge>Guardada</Badge> : null}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={saving || suggestion.saved}
                    onClick={() => onSave(suggestion)}
                  >
                    <Save className="h-4 w-4" />
                    Guardar bloque
                  </Button>
                  <Button size="sm" variant="ghost" disabled={saving} onClick={() => onDiscard(suggestion.localId)}>
                    Descartar
                  </Button>
                </div>
              </div>
              <div className="mt-3 space-y-2">
                <Input
                  value={suggestion.title}
                  onChange={(event) => onSuggestionChange(suggestion.localId, { title: event.target.value })}
                  placeholder="Titulo del bloque"
                />
                <textarea
                  value={suggestion.quote_text ?? ""}
                  onChange={(event) => onSuggestionChange(suggestion.localId, { quote_text: event.target.value || null })}
                  placeholder="Cita literal corta, solo si esta verificada"
                  className="min-h-16 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
                <textarea
                  value={suggestion.content}
                  onChange={(event) => onSuggestionChange(suggestion.localId, { content: event.target.value })}
                  placeholder="Contenido editable"
                  className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <SourceLine
                title={suggestion.source_title}
                author={suggestion.source_author}
                reference={suggestion.source_reference}
              />
              {isSuggestedReference(suggestion.source_status) ? (
                <p className="mt-3 text-xs text-amber-700 dark:text-amber-200">
                  Referencia no verificada localmente. Revisala antes de usarla como cita o fuente exacta.
                </p>
              ) : null}
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function WorkspaceSummary({ workspace, loading }: { workspace?: StudyWorkspace; loading: boolean }) {
  if (loading) return <Card className="p-4 text-sm text-muted-foreground">Cargando estudio...</Card>;
  if (!workspace) return null;
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{workspace.title || workspace.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{workspace.scriptureReference || "Sin escritura base"}</p>
        </div>
        {workspace.topic ? <Badge>{workspace.topic}</Badge> : null}
      </div>
      {workspace.personalThought ? (
        <p className="mt-4 rounded-md border bg-muted/40 p-3 text-sm leading-6 text-muted-foreground">{workspace.personalThought}</p>
      ) : null}
      {workspace.callingContext ? (
        <p className="mt-3 text-sm text-muted-foreground">Llamamiento/contexto: {workspace.callingContext}</p>
      ) : null}
    </Card>
  );
}

function StudyBlockCard({
  block,
  editing,
  onEdit,
  onSave,
  onDelete
}: {
  block: StudyBlock;
  editing: StudyBlock | null;
  onEdit: (block: StudyBlock | null) => void;
  onSave: (block: StudyBlock) => void;
  onDelete: () => void;
}) {
  if (editing) {
    return (
      <Card className="p-4">
        <div className="space-y-2">
          <Input value={editing.title} onChange={(event) => onEdit({ ...editing, title: event.target.value })} />
          <textarea
            value={editing.quoteText ?? ""}
            onChange={(event) => onEdit({ ...editing, quoteText: event.target.value })}
            placeholder="Cita literal corta, si aplica"
            className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <textarea
            value={editing.content}
            onChange={(event) => onEdit({ ...editing, content: event.target.value })}
            className="min-h-32 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={() => onSave(editing)}>
              <Save className="h-4 w-4" />
              Guardar
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onEdit(null)}>
              Cancelar
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn("p-4", block.type === "post_it" && "border-yellow-300 bg-yellow-50 dark:bg-yellow-950/20")}>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge>{blockLabels[block.type] || "Bloque"}</Badge>
            {block.isAiGenerated ? <Badge>IA</Badge> : <Badge>Manual</Badge>}
          </div>
          <h3 className="mt-2 font-semibold">{block.title}</h3>
        </div>
        <div className="flex flex-wrap gap-1">
          <Button size="sm" variant="outline" onClick={() => onEdit(block)}>
            Editar
          </Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>
            <Trash2 className="h-4 w-4" />
            Eliminar
          </Button>
        </div>
      </div>
      {block.quoteText ? <blockquote className="mt-3 border-l-2 pl-3 text-sm">{block.quoteText}</blockquote> : null}
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{block.content}</p>
      <SourceLine title={block.sourceTitle} author={block.sourceAuthor} reference={block.sourceReference} />
    </Card>
  );
}

function SourceLine({
  title,
  author,
  reference
}: {
  title?: string | null;
  author?: string | null;
  reference?: string | null;
}) {
  if (!title && !author && !reference) return null;
  return <p className="mt-3 text-xs text-muted-foreground">Fuente: {[title, author, reference].filter(Boolean).join(" - ")}</p>;
}

function renderStudyMarkdown(workspace: StudyWorkspace, blocks: StudyBlock[]) {
  const lines = [`# ${workspace.title || workspace.name}`, ""];
  if (workspace.scriptureReference) lines.push(`**Escritura base:** ${workspace.scriptureReference}`, "");
  if (workspace.personalThought) lines.push("## Mi pensamiento", "", workspace.personalThought, "");
  for (const block of blocks) {
    lines.push(`## ${block.title}`, "");
    if (block.quoteText) lines.push(`> ${block.quoteText}`, "");
    if (block.content) lines.push(block.content, "");
    const source = [block.sourceTitle, block.sourceAuthor, block.sourceReference].filter(Boolean).join(" - ");
    if (source) lines.push(`Fuente: ${source}`, "");
  }
  return lines.join("\n");
}

"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, BookOpen, Download, Plus, Save, Sparkles, StickyNote, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { studyApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import type { AiSuggestedBlock, AiSuggestionMode, StudyBlock, StudyBlockType, StudyProject } from "@/types/study";

type Props = {
  workspaceId?: string;
};

const blockLabels: Record<StudyBlockType, string> = {
  personal_note: "Nota personal",
  ai_doctrinal_analysis: "Analisis doctrinal",
  ai_quote: "Cita sugerida",
  ai_reference: "Referencia",
  scripture_connection: "Conexion con pasajes",
  reflection_question: "Pregunta de reflexion",
  powerful_phrase: "Frase poderosa",
  name_meaning: "Significado de nombres",
  calling_application: "Aplicacion al llamamiento",
  manual_reference: "Manual",
  book_reference: "Libro"
};

export function StudyWorkspaceExperience({ workspaceId: routeProjectId }: Props) {
  const queryClient = useQueryClient();
  const userId = useStudyWorkspaceStore((state) => state.userId);
  const [manualBlock, setManualBlock] = useState({ title: "", content: "", quoteText: "" });
  const [postIt, setPostIt] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<AiSuggestionMode>("rapido");
  const [editingBlock, setEditingBlock] = useState<StudyBlock | null>(null);
  const [suggestions, setSuggestions] = useState<AiSuggestedBlock[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  const projects = useQuery({
    queryKey: ["study-projects", userId],
    queryFn: () => studyApi.projects(userId)
  });

  const projectId = routeProjectId ?? projects.data?.items[0]?.id;
  const project = useQuery({
    queryKey: ["study-project", userId, projectId],
    queryFn: () => studyApi.project(userId, projectId as string),
    enabled: Boolean(projectId)
  });

  const activeProject = project.data;
  const blocks = useMemo(() => activeProject?.blocks ?? [], [activeProject?.blocks]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["study-projects"] });
    queryClient.invalidateQueries({ queryKey: ["study-project", userId, projectId] });
  };

  const suggest = useMutation({
    mutationFn: () =>
      studyApi.suggestBlocks(userId, projectId as string, {
        prompt: prompt.trim() || undefined,
        mode,
        maxSuggestions: 10
      }),
    onSuccess: (response) => {
      setSuggestions(response.suggestions);
      setWarnings(response.warnings);
    }
  });

  const saveSuggestion = useMutation({
    mutationFn: ({ suggestion, index }: { suggestion: AiSuggestedBlock; index: number }) =>
      studyApi.saveSuggestion(userId, projectId as string, suggestion, blocks.length * 10 + index * 10 + 10),
    onSuccess: (_block, variables) => {
      setSuggestions((items) => items.filter((item) => item !== variables.suggestion));
      invalidate();
    }
  });

  const saveAllSuggestions = useMutation({
    mutationFn: async () => {
      for (const [index, suggestion] of suggestions.entries()) {
        await studyApi.saveSuggestion(userId, projectId as string, suggestion, blocks.length * 10 + index * 10 + 10);
      }
    },
    onSuccess: () => {
      setSuggestions([]);
      invalidate();
    }
  });

  const createManualCitation = useMutation({
    mutationFn: () =>
      studyApi.createBlock(userId, projectId as string, {
        type: "ai_quote",
        title: manualBlock.title.trim() || "Cita manual",
        quoteText: manualBlock.quoteText.trim(),
        content: manualBlock.content.trim(),
        isAiGenerated: false,
        metadata: { sourceStatus: "usuario" }
      }),
    onSuccess: () => {
      setManualBlock({ title: "", content: "", quoteText: "" });
      invalidate();
    }
  });

  const createPostIt = useMutation({
    mutationFn: () =>
      studyApi.createBlock(userId, projectId as string, {
        type: "personal_note",
        title: "Post-it",
        content: postIt.trim(),
        isAiGenerated: false,
        metadata: { display: "post_it", color: "yellow" }
      }),
    onSuccess: () => {
      setPostIt("");
      invalidate();
    }
  });

  const updateBlock = useMutation({
    mutationFn: (block: Partial<StudyBlock> & { id: string }) =>
      studyApi.updateBlock(userId, projectId as string, block.id, block),
    onSuccess: () => {
      setEditingBlock(null);
      invalidate();
    }
  });

  const deleteBlock = useMutation({
    mutationFn: (blockId: string) => studyApi.deleteBlock(userId, projectId as string, blockId),
    onSuccess: invalidate
  });

  const archiveProject = useMutation({
    mutationFn: () => studyApi.archiveProject(userId, projectId as string),
    onSuccess: invalidate
  });

  const exportMarkdown = () => {
    if (!activeProject) return;
    const markdown = renderStudyMarkdown(activeProject, blocks);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${activeProject.title.toLowerCase().replace(/[^a-z0-9]+/gi, "-") || "estudio"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!projectId && !projects.isLoading) {
    return (
      <EmptyStudyState />
    );
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Mesa de Estudio Doctrinal</p>
          <h1 className="text-2xl font-semibold">Mis Estudios</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Crea bloques editables de estudio personal. La IA sugiere; tu decides que guardar, editar o descartar.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/study/new">
            <Button>
              <Plus className="h-4 w-4" />
              Nuevo estudio
            </Button>
          </Link>
          <Button variant="outline" disabled={!activeProject} onClick={exportMarkdown}>
            <Download className="h-4 w-4" />
            Exportar estudio
          </Button>
          <Button variant="ghost" disabled={!activeProject || archiveProject.isPending} onClick={() => archiveProject.mutate()}>
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
              {projects.data?.items.map((item) => (
                <Link
                  key={item.id}
                  href={`/study/${item.id}`}
                  className={cn(
                    "block rounded-md border p-3 text-sm transition hover:bg-muted",
                    item.id === projectId && "border-primary bg-primary/10"
                  )}
                >
                  <span className="line-clamp-2 font-medium">{item.title}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {item.scriptureReference || item.topic || "Sin referencia"}
                  </span>
                </Link>
              ))}
              {projects.isLoading ? <p className="text-sm text-muted-foreground">Cargando estudios...</p> : null}
            </div>
          </Card>
        </aside>

        <main className="space-y-4">
          <ProjectSummary project={activeProject} loading={project.isLoading} />
          <Card className="p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="font-semibold">Bloques del estudio</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Edita, guarda, descarta o reordena cualquier bloque.
                </p>
              </div>
              <Button disabled={!projectId || suggest.isPending} onClick={() => suggest.mutate()}>
                <Sparkles className="h-4 w-4" />
                Anadir informacion con IA
              </Button>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_180px]">
              <Input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Prompt opcional para la IA" />
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value as AiSuggestionMode)}
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="rapido">Rapido</option>
                <option value="profundo">Profundo</option>
                <option value="citas">Citas</option>
                <option value="manuales">Manuales</option>
                <option value="nombres">Nombres</option>
                <option value="llamamiento">Llamamiento</option>
              </select>
            </div>
            {warnings.length ? (
              <div className="mt-3 rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
                {warnings.map((warning) => (
                  <p key={warning}>{warning}</p>
                ))}
              </div>
            ) : null}
          </Card>

          {suggestions.length ? (
            <Card className="p-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">Sugerencias pendientes</h2>
                <Button size="sm" disabled={saveAllSuggestions.isPending} onClick={() => saveAllSuggestions.mutate()}>
                  Guardar todo
                </Button>
              </div>
              <div className="mt-4 grid gap-3">
                {suggestions.map((suggestion, index) => (
                  <SuggestionCard
                    key={`${suggestion.type}-${suggestion.title}-${index}`}
                    suggestion={suggestion}
                    onSave={() => saveSuggestion.mutate({ suggestion, index })}
                    onDiscard={() => setSuggestions((items) => items.filter((item) => item !== suggestion))}
                  />
                ))}
              </div>
            </Card>
          ) : null}

          <div className="grid gap-3">
            {blocks.map((block) => (
              <StudyBlockCard
                key={block.id}
                block={block}
                editing={editingBlock?.id === block.id ? editingBlock : null}
                onEdit={setEditingBlock}
                onSave={(next) => updateBlock.mutate(next)}
                onDelete={() => deleteBlock.mutate(block.id)}
                onMove={(direction) => updateBlock.mutate({ id: block.id, sortOrder: block.sortOrder + direction * 15 })}
              />
            ))}
            {!project.isLoading && blocks.length === 0 ? (
              <p className="rounded-md border p-4 text-sm text-muted-foreground">
                Todavia no hay bloques. Agrega una nota manual o pide sugerencias con IA.
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
                placeholder="Cita corta o referencia privada"
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
                disabled={!projectId || !manualBlock.quoteText.trim() || createManualCitation.isPending}
                onClick={() => createManualCitation.mutate()}
              >
                <BookOpen className="h-4 w-4" />
                Guardar cita
              </Button>
            </div>
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
            <Button className="mt-2 w-full" variant="outline" disabled={!projectId || !postIt.trim()} onClick={() => createPostIt.mutate()}>
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
      <h1 className="mt-2 text-2xl font-semibold">Aun no tienes estudios</h1>
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

function ProjectSummary({ project, loading }: { project?: StudyProject; loading: boolean }) {
  if (loading) return <Card className="p-4 text-sm text-muted-foreground">Cargando estudio...</Card>;
  if (!project) return null;
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{project.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{project.scriptureReference || "Sin escritura base"}</p>
        </div>
        {project.topic ? <Badge>{project.topic}</Badge> : null}
      </div>
      {project.personalThought ? (
        <p className="mt-4 rounded-md border bg-muted/40 p-3 text-sm leading-6 text-muted-foreground">{project.personalThought}</p>
      ) : null}
      {project.callingContext ? (
        <p className="mt-3 text-sm text-muted-foreground">Llamamiento/contexto: {project.callingContext}</p>
      ) : null}
    </Card>
  );
}

function SuggestionCard({
  suggestion,
  onSave,
  onDiscard
}: {
  suggestion: AiSuggestedBlock;
  onSave: () => void;
  onDiscard: () => void;
}) {
  return (
    <div className="rounded-md border p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <Badge className="border-primary/30 bg-primary/10 text-primary">{blockLabels[suggestion.type]}</Badge>
          <h3 className="mt-2 font-semibold">{suggestion.title}</h3>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={onSave}>Guardar</Button>
          <Button size="sm" variant="ghost" onClick={onDiscard}>Descartar</Button>
        </div>
      </div>
      {suggestion.quoteText ? <blockquote className="mt-3 border-l-2 pl-3 text-sm">{suggestion.quoteText}</blockquote> : null}
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{suggestion.content}</p>
      <SourceLine
        title={suggestion.sourceTitle}
        author={suggestion.sourceAuthor}
        reference={suggestion.sourceReference}
        status={suggestion.sourceStatus}
      />
    </div>
  );
}

function StudyBlockCard({
  block,
  editing,
  onEdit,
  onSave,
  onDelete,
  onMove
}: {
  block: StudyBlock;
  editing: StudyBlock | null;
  onEdit: (block: StudyBlock | null) => void;
  onSave: (block: StudyBlock) => void;
  onDelete: () => void;
  onMove: (direction: -1 | 1) => void;
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
            <Button size="sm" variant="ghost" onClick={() => onEdit(null)}>Cancelar</Button>
          </div>
        </div>
      </Card>
    );
  }

  const sourceStatus = typeof block.metadata.sourceStatus === "string" ? block.metadata.sourceStatus : undefined;
  return (
    <Card className={cn("p-4", block.metadata.display === "post_it" && "border-yellow-300 bg-yellow-50 dark:bg-yellow-950/20")}>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge className={block.isAiGenerated ? "border-primary/30 bg-primary/10 text-primary" : undefined}>
              {blockLabels[block.type]}
            </Badge>
            {block.isAiGenerated ? <Badge>IA</Badge> : <Badge>Manual</Badge>}
          </div>
          <h3 className="mt-2 font-semibold">{block.title}</h3>
        </div>
        <div className="flex flex-wrap gap-1">
          <Button size="icon" variant="ghost" onClick={() => onMove(-1)} aria-label="Mover arriba">
            <ArrowUp className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" onClick={() => onMove(1)} aria-label="Mover abajo">
            <ArrowDown className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" onClick={() => onEdit(block)}>Editar</Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>
            <Trash2 className="h-4 w-4" />
            Eliminar
          </Button>
        </div>
      </div>
      {block.quoteText ? <blockquote className="mt-3 border-l-2 pl-3 text-sm">{block.quoteText}</blockquote> : null}
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{block.content}</p>
      <SourceLine title={block.sourceTitle} author={block.sourceAuthor} reference={block.sourceReference} status={sourceStatus} />
    </Card>
  );
}

function SourceLine({
  title,
  author,
  reference,
  status
}: {
  title?: string | null;
  author?: string | null;
  reference?: string | null;
  status?: string | null;
}) {
  if (!title && !author && !reference && !status) return null;
  return (
    <p className="mt-3 text-xs text-muted-foreground">
      Fuente: {[title, author, reference].filter(Boolean).join(" - ") || "sin fuente local"}{" "}
      {status ? <span className="font-medium">({status})</span> : null}
    </p>
  );
}

function renderStudyMarkdown(project: StudyProject, blocks: StudyBlock[]) {
  const lines = [`# ${project.title}`, ""];
  if (project.scriptureReference) lines.push(`**Escritura base:** ${project.scriptureReference}`, "");
  if (project.personalThought) lines.push("## Mi pensamiento", "", project.personalThought, "");
  for (const block of blocks) {
    lines.push(`## ${block.title}`, "");
    if (block.quoteText) lines.push(`> ${block.quoteText}`, "");
    if (block.content) lines.push(block.content, "");
    const source = [block.sourceTitle, block.sourceAuthor, block.sourceReference].filter(Boolean).join(" - ");
    if (source) lines.push(`Fuente: ${source}`, "");
  }
  return lines.join("\n");
}

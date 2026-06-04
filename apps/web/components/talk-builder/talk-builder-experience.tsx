"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpenCheck, Download, FileText, RefreshCw, Save, ScrollText, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { downloadBlob, exportsApi, ragApi, studyApi, talkBuilderApi } from "@/lib/api";
import { mergeSourceOptions } from "@/lib/source-filters";
import { cn, truncate } from "@/lib/utils";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import type { TalkBuilderOutline, TalkBuilderSection } from "@/types/talk-builder";

type FormState = {
  topic: string;
  audience: string;
  durationMinutes: number;
  language: string;
  scriptureRefs: string;
  sourceType: string;
  workspaceId: string;
};

const initialForm: FormState = {
  topic: "",
  audience: "Jovenes y adultos",
  durationMinutes: 10,
  language: "es",
  scriptureRefs: "",
  sourceType: "",
  workspaceId: ""
};

export function TalkBuilderExperience() {
  const { userId, activeWorkspaceId, setActiveWorkspaceId } = useStudyWorkspaceStore();
  const [form, setForm] = useState<FormState>({ ...initialForm, workspaceId: activeWorkspaceId ?? "" });
  const [outline, setOutline] = useState<TalkBuilderOutline | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const workspaces = useQuery({
    queryKey: ["talk-builder-workspaces", userId],
    queryFn: () => studyApi.workspaces(userId)
  });
  const sources = useQuery({ queryKey: ["source-options"], queryFn: () => ragApi.sourcesSummary(), staleTime: 1000 * 60 });

  const generate = useMutation({
    mutationFn: () =>
      talkBuilderApi.outline(userId, {
        topic: form.topic.trim(),
        audience: form.audience.trim(),
        durationMinutes: form.durationMinutes,
        language: form.language.trim() || undefined,
        workspaceId: form.workspaceId || undefined,
        scriptureRefs: splitRefs(form.scriptureRefs),
        sourceTypes: form.sourceType ? [form.sourceType] : []
      }),
    onSuccess: (data) => {
      setOutline(data);
      setSaveMessage(null);
    }
  });

  const saveDraft = useMutation({
    mutationFn: () =>
      talkBuilderApi.saveDraft(userId, {
        title: outline?.title ?? `Bosquejo: ${form.topic}`,
        workspaceId: form.workspaceId || undefined,
        outline: outline as TalkBuilderOutline,
        content: outlineToMarkdown(outline as TalkBuilderOutline),
        scriptureRefs: outline?.scriptureRefs ?? splitRefs(form.scriptureRefs)
      }),
    onSuccess: (data) => {
      setSaveMessage("Borrador guardado en StudyWorkspace.");
      if (!form.workspaceId) {
        setForm((value) => ({ ...value, workspaceId: data.workspaceId }));
      }
      setActiveWorkspaceId(data.workspaceId);
    }
  });

  const exportTalkDrafts = useMutation({
    mutationFn: (format: "markdown" | "pdf") =>
      exportsApi.study(userId, {
        workspaceId: form.workspaceId || activeWorkspaceId || "",
        kind: "talk_drafts",
        format
      }),
    onSuccess: (file) => {
      downloadBlob(file);
      setExportMessage("Borradores exportados con sus fuentes.");
    },
    onError: (error) => {
      setExportMessage(error instanceof Error ? error.message : "No se pudieron exportar los borradores.");
    }
  });

  const canGenerate = form.topic.trim().length > 1 && !generate.isPending;
  const canSave = outline?.status === "ready" && outline.sections.length > 0 && !saveDraft.isPending;
  const canExportDrafts = Boolean(form.workspaceId || activeWorkspaceId) && !exportTalkDrafts.isPending;
  const sourceOptions = useMemo(() => mergeSourceOptions(sources.data?.items), [sources.data?.items]);

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Talk Builder</p>
          <h1 className="text-2xl font-semibold">Constructor de discursos doctrinales</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Crea bosquejos editables usando documentos, referencias y citas guardadas reales de Gospel Library IA.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => generate.reset()}>
            <RefreshCw className="h-4 w-4" />
            Limpiar estado
          </Button>
          <Button disabled={!canSave} onClick={() => saveDraft.mutate()}>
            <Save className="h-4 w-4" />
            Guardar borrador
          </Button>
          <Button variant="outline" disabled={!canExportDrafts} onClick={() => exportTalkDrafts.mutate("markdown")}>
            <Download className="h-4 w-4" />
            Markdown
          </Button>
          <Button variant="outline" disabled={!canExportDrafts} onClick={() => exportTalkDrafts.mutate("pdf")}>
            <Download className="h-4 w-4" />
            PDF
          </Button>
        </div>
      </header>

      <section className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center gap-2">
              <ScrollText className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Parametros</h2>
            </div>
            <div className="mt-4 space-y-3">
              <Input
                value={form.topic}
                onChange={(event) => setForm((value) => ({ ...value, topic: event.target.value }))}
                placeholder="Tema del discurso"
              />
              <Input
                value={form.audience}
                onChange={(event) => setForm((value) => ({ ...value, audience: event.target.value }))}
                placeholder="Audiencia"
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  min={3}
                  max={45}
                  value={form.durationMinutes}
                  onChange={(event) =>
                    setForm((value) => ({ ...value, durationMinutes: Number(event.target.value) || 10 }))
                  }
                  placeholder="Minutos"
                />
                <Input
                  value={form.language}
                  onChange={(event) => setForm((value) => ({ ...value, language: event.target.value }))}
                  placeholder="Idioma"
                />
              </div>
              <Input
                value={form.scriptureRefs}
                onChange={(event) => setForm((value) => ({ ...value, scriptureRefs: event.target.value }))}
                placeholder="Referencias, separadas por coma"
              />
              <select
                value={form.sourceType}
                onChange={(event) => setForm((value) => ({ ...value, sourceType: event.target.value }))}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                aria-label="Fuente"
              >
                <option value="">Todas las fuentes</option>
                {sourceOptions.map((source) => (
                  <option key={source.key} value={source.key}>
                    {source.label}
                    {typeof source.documentCount === "number" ? ` (${source.documentCount})` : ""}
                  </option>
                ))}
              </select>
              <select
                value={form.workspaceId}
                onChange={(event) => setForm((value) => ({ ...value, workspaceId: event.target.value }))}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                aria-label="Workspace"
              >
                <option value="">Guardar en workspace automatico</option>
                {workspaces.data?.items.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
              <Button className="w-full" disabled={!canGenerate} onClick={() => generate.mutate()}>
                <Sparkles className="h-4 w-4" />
                Generar bosquejo
              </Button>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2">
              <BookOpenCheck className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Fuentes usadas</h2>
            </div>
            <div className="mt-4 space-y-3">
              {outline?.sources.map((source) => (
                <a
                  key={source.id}
                  href={source.sourceUrl ?? source.canonicalUrl ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-md border p-3 text-sm transition hover:bg-muted"
                >
                  <span className="font-medium">{source.title}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {source.author ?? "Autor desconocido"} - {source.sourceType ?? source.sourceName ?? "Fuente"}
                  </span>
                  {source.excerpt ? <span className="mt-2 block text-xs text-muted-foreground">{truncate(source.excerpt, 180)}</span> : null}
                </a>
              ))}
              {!outline ? <p className="text-sm text-muted-foreground">Genera un bosquejo para ver fuentes reales.</p> : null}
              {outline && outline.sources.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay documentos reales para este tema.</p>
              ) : null}
            </div>
          </Card>
        </aside>

        <main className="space-y-4">
          {generate.error ? (
            <StatusPanel tone="error" message={generate.error instanceof Error ? generate.error.message : "No se pudo generar el bosquejo."} />
          ) : null}
          {outline?.warnings.map((warning) => <StatusPanel key={warning} tone="warning" message={warning} />)}
          {saveDraft.error ? (
            <StatusPanel tone="error" message={saveDraft.error instanceof Error ? saveDraft.error.message : "No se pudo guardar."} />
          ) : null}
          {saveMessage ? <StatusPanel tone="success" message={saveMessage} /> : null}
          {exportMessage ? <StatusPanel tone="success" message={exportMessage} /> : null}

          <Card className="p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-lg font-semibold">{outline?.title ?? "Bosquejo pendiente"}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {outline ? `${outline.durationMinutes} minutos - ${outline.audience}` : "Configura el tema y genera una propuesta editable."}
                </p>
              </div>
              {outline?.status ? <Badge>{outline.status === "ready" ? "Listo" : "Sin fuentes"}</Badge> : null}
            </div>

            <div className="mt-4 space-y-3">
              {!outline ? (
                <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
                  El builder citara documentos o citas guardadas reales. No usa OpenAI cuando el sistema esta sin credito.
                </div>
              ) : null}
              {outline?.sections.map((section, index) => (
                <SectionEditor
                  key={section.id}
                  section={section}
                  index={index}
                  onChange={(next) => updateSection(outline, setOutline, index, next)}
                />
              ))}
              {outline?.status === "unavailable" ? (
                <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
                  Cambia el tema, agrega una referencia escritural o guarda citas en StudyWorkspace para generar un bosquejo con grounding.
                </div>
              ) : null}
            </div>
          </Card>
        </main>
      </section>
    </div>
  );
}

function SectionEditor({
  section,
  index,
  onChange
}: {
  section: TalkBuilderSection;
  index: number;
  onChange: (section: TalkBuilderSection) => void;
}) {
  return (
    <div className="rounded-md border p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <FileText className="h-4 w-4 text-primary" />
        Seccion {index + 1}
      </div>
      <Input
        className="mt-3 font-medium"
        value={section.title}
        onChange={(event) => onChange({ ...section, title: event.target.value })}
      />
      <textarea
        value={section.purpose}
        onChange={(event) => onChange({ ...section, purpose: event.target.value })}
        className="mt-2 min-h-16 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
      />
      <div className="mt-3 space-y-2">
        {section.talkingPoints.map((point, pointIndex) => (
          <textarea
            key={`${section.id}-${pointIndex}`}
            value={point}
            onChange={(event) => {
              const nextPoints = [...section.talkingPoints];
              nextPoints[pointIndex] = event.target.value;
              onChange({ ...section, talkingPoints: nextPoints });
            }}
            className="min-h-12 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        ))}
      </div>
      {section.suggestedQuote ? (
        <blockquote className="mt-3 rounded-md border-l-4 border-primary bg-muted/40 p-3 text-sm text-muted-foreground">
          {truncate(section.suggestedQuote, 360)}
        </blockquote>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {section.citations.map((citation) => (
          <a
            key={citation.id}
            href={citation.url ?? "#"}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <BookOpenCheck className="h-3.5 w-3.5" />
            {citation.title}
          </a>
        ))}
      </div>
    </div>
  );
}

function StatusPanel({ message, tone }: { message: string; tone: "warning" | "error" | "success" }) {
  return (
    <div
      className={cn(
        "rounded-md border px-4 py-3 text-sm",
        tone === "warning" && "border-amber-300 bg-amber-50 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100",
        tone === "error" && "border-destructive/40 bg-destructive/10 text-destructive",
        tone === "success" && "border-emerald-300 bg-emerald-50 text-emerald-950 dark:bg-emerald-950/30 dark:text-emerald-100"
      )}
    >
      {message}
    </div>
  );
}

function updateSection(
  outline: TalkBuilderOutline,
  setOutline: (outline: TalkBuilderOutline) => void,
  index: number,
  section: TalkBuilderSection
) {
  const sections = [...outline.sections];
  sections[index] = section;
  setOutline({ ...outline, sections });
}

function splitRefs(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function outlineToMarkdown(outline: TalkBuilderOutline) {
  return [
    `# ${outline.title}`,
    "",
    `Audiencia: ${outline.audience}`,
    `Duracion: ${outline.durationMinutes} minutos`,
    "",
    ...outline.sections.flatMap((section) => [
      `## ${section.title}`,
      section.purpose,
      "",
      ...section.talkingPoints.map((point) => `- ${point}`),
      ...section.citations.map((citation) => `- Fuente: ${citation.title}${citation.author ? `, ${citation.author}` : ""}`),
      ""
    ])
  ].join("\n");
}

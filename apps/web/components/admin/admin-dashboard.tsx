"use client";

import { useMemo, useState } from "react";
import type { ElementType } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  DollarSign,
  FileText,
  Globe2,
  MessageSquare as MessageIcon,
  NotebookPen as NotebookIcon,
  PauseCircle,
  Play,
  PlayCircle,
  RefreshCw,
  RotateCcw,
  Save,
  Server,
  Tags,
  Users
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";
import { cn, truncate } from "@/lib/utils";

function asNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value ?? 0);
}

function formatCount(value: unknown): string {
  return new Intl.NumberFormat("es").format(asNumber(value));
}

function textValue(value: unknown, fallback = "sin dato") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function taskLabel(task: Record<string, unknown>) {
  return String(task.type ?? task.job_type ?? task.id ?? "Tarea");
}

function taskTime(task: Record<string, unknown>) {
  const raw = task.finishedAt ?? task.startedAt ?? task.createdAt;
  return raw ? new Date(String(raw)).toLocaleString() : "sin fecha";
}

export function AdminDashboard() {
  const queryClient = useQueryClient();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [sourceLimits, setSourceLimits] = useState<Record<string, number>>({});
  const status = useQuery({ queryKey: ["admin-status"], queryFn: () => ragApi.adminStatus(), refetchInterval: 15000 });
  const ingestion = useQuery({ queryKey: ["ingestion-status"], queryFn: () => ragApi.ingestionStatus(), refetchInterval: 15000 });
  const errors = useQuery({ queryKey: ["admin-errors"], queryFn: () => ragApi.adminErrors(), refetchInterval: 15000 });
  const documentSummary = useQuery({ queryKey: ["documents-summary"], queryFn: () => ragApi.documentsSummary(), refetchInterval: 15000 });
  const documents = useQuery({ queryKey: ["admin-documents"], queryFn: () => ragApi.documents({ limit: 1, offset: 0 }), refetchInterval: 15000 });
  const authors = useQuery({ queryKey: ["admin-authors"], queryFn: () => ragApi.authors(), refetchInterval: 15000 });
  const topics = useQuery({ queryKey: ["admin-topics"], queryFn: () => ragApi.topics(), refetchInterval: 15000 });
  const sources = useQuery({ queryKey: ["admin-sources"], queryFn: () => ragApi.sourcesSummary(), refetchInterval: 15000 });
  const sourceCatalog = useQuery({
    queryKey: ["admin-source-catalog"],
    queryFn: () => ragApi.adminSources(),
    refetchInterval: 15000
  });
  const cost = useQuery({ queryKey: ["admin-cost"], queryFn: () => ragApi.adminCost(), refetchInterval: 15000 });
  const beta = useQuery({ queryKey: ["admin-beta"], queryFn: () => ragApi.adminBeta(), refetchInterval: 15000 });
  const estimate = useQuery({
    queryKey: ["admin-indexing-estimate"],
    queryFn: () => ragApi.indexingEstimate({ limit: 100, force: false }),
    refetchInterval: 30000
  });
  const scrape = useMutation({
    mutationFn: () => ragApi.scrape(),
    onSuccess: (data) => {
      setActionMessage(`Scraping encolado: ${data.task_id}`);
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo ejecutar scraping.")
  });
  const reindex = useMutation({
    mutationFn: () => ragApi.reindex(),
    onSuccess: (data) => {
      setActionMessage(`Reindexado encolado: ${data.task_id}`);
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo reindexar.")
  });
  const pauseIndexing = useMutation({
    mutationFn: () => ragApi.pauseIndexing(),
    onSuccess: () => {
      setActionMessage("Indexing pausado.");
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo pausar indexing.")
  });
  const resumeIndexing = useMutation({
    mutationFn: () => ragApi.resumeIndexing(),
    onSuccess: () => {
      setActionMessage("Indexing reanudado.");
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo reanudar indexing.")
  });
  const retry = useMutation({
    mutationFn: (jobId: string) => ragApi.retryJob(jobId),
    onSuccess: (data) => {
      setActionMessage(`Reintento encolado: ${data.task_id}`);
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo reintentar la tarea.")
  });
  const updateSource = useMutation({
    mutationFn: ({ sourceId, payload }: { sourceId: string; payload: { enabled?: boolean; maxPagesPerRun?: number } }) =>
      ragApi.updateAdminSource(sourceId, payload),
    onSuccess: (data) => {
      setActionMessage(`Fuente actualizada: ${data.sourceId}`);
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo actualizar la fuente.")
  });
  const crawlSource = useMutation({
    mutationFn: ({ sourceId, maxPagesPerRun }: { sourceId: string; maxPagesPerRun?: number }) =>
      ragApi.crawlSource(sourceId, maxPagesPerRun ? { maxPagesPerRun } : undefined),
    onSuccess: (data) => {
      setActionMessage(`Crawl encolado para ${data.sourceId}: ${data.task_id}`);
      refreshAll();
    },
    onError: (error) => setActionMessage(error instanceof Error ? error.message : "No se pudo ejecutar el crawl de fuente.")
  });

  const documentStatuses = documentSummary.data?.documents ?? [];
  const totalDocuments = documents.data?.total ?? status.data?.postgres?.documents ?? 0;
  const authorCount = authors.data?.items?.length ?? 0;
  const topicCount = topics.data?.items?.length ?? 0;
  const qdrantVectors = status.data?.qdrant?.vectors ?? 0;
  const postgresErrors = status.data?.postgres?.errors ?? 0;
  const qdrantStatus = String(status.data?.qdrant?.status ?? (status.isLoading ? "loading" : "unknown"));
  const postgresDatabase = String(status.data?.postgres?.database ?? "unknown");
  const indexingState = (cost.data?.indexing ?? {}) as Record<string, unknown>;
  const indexingPaused = Boolean(indexingState.paused);
  const embeddingGenerated = Array.isArray(cost.data?.usageByKind)
    ? cost.data.usageByKind.find((item) => item && typeof item === "object" && (item as Record<string, unknown>).kind === "embedding")
    : undefined;
  const failedJobs = errors.data?.jobs ?? [];
  const failedDocuments = errors.data?.documents ?? [];
  const latestScrapingTasks = useMemo(() => {
    const fromEndpoint = ingestion.data?.latestScrapingTasks ?? [];
    const fromButton = scrape.data ? [{ id: scrape.data.task_id, type: "scrape", status: "queued" }] : [];
    return [...fromButton, ...fromEndpoint].slice(0, 8);
  }, [ingestion.data, scrape.data]);
  const latestIndexingTasks = useMemo(() => {
    const fromEndpoint = ingestion.data?.latestIndexingTasks ?? [];
    const fromButton = reindex.data ? [{ id: reindex.data.task_id, type: "index", status: "queued" }] : [];
    return [...fromButton, ...fromEndpoint].slice(0, 8);
  }, [ingestion.data, reindex.data]);

  function refreshAll() {
    void queryClient.invalidateQueries({ queryKey: ["admin-status"] });
    void queryClient.invalidateQueries({ queryKey: ["ingestion-status"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-errors"] });
    void queryClient.invalidateQueries({ queryKey: ["documents-summary"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-authors"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-topics"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-sources"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-source-catalog"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-cost"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-indexing-estimate"] });
    void queryClient.invalidateQueries({ queryKey: ["admin-beta"] });
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard admin</h1>
          <p className="text-sm text-muted-foreground">Operacion de ingesta, embeddings, busqueda y RAG con datos reales.</p>
        </div>
        <AdminActions
          onRefresh={refreshAll}
          onScrape={() => scrape.mutate()}
          onReindex={() => reindex.mutate()}
          scraping={scrape.isPending}
          reindexing={reindex.isPending}
        />
      </div>

      {actionMessage ? <p className="rounded-md border bg-card px-4 py-3 text-sm text-muted-foreground">{actionMessage}</p> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard icon={FileText} label="Documentos" value={formatCount(totalDocuments)} />
        <MetricCard icon={Users} label="Autores" value={formatCount(authorCount)} />
        <MetricCard icon={Tags} label="Temas" value={formatCount(topicCount)} />
        <MetricCard icon={Database} label="Vectores Qdrant" value={formatCount(qdrantVectors)} />
        <MetricCard icon={Server} label="PostgreSQL" value={postgresDatabase} compact />
        <MetricCard icon={AlertCircle} label="Errores" value={formatCount(postgresErrors)} tone={asNumber(postgresErrors) ? "danger" : "ok"} />
      </div>

      <Card className="p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Datos cargados</h2>
            <p className="text-sm text-muted-foreground">Estado actual de documentos, autores, temas, vectores y tareas.</p>
          </div>
          <AdminActions
            onRefresh={refreshAll}
            onScrape={() => scrape.mutate()}
            onReindex={() => reindex.mutate()}
            scraping={scrape.isPending}
            reindexing={reindex.isPending}
          />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
          <StatusPanel title="Documentos por estado" items={documentStatuses.map((item) => [item.status, item.count])} />
          <HealthPanel
            title="Qdrant"
            status={qdrantStatus}
            rows={[
              ["Coleccion", status.data?.qdrant?.collection],
              ["Vectores", formatCount(qdrantVectors)],
              ["Dimension", status.data?.qdrant?.dimensions]
            ]}
          />
          <HealthPanel
            title="PostgreSQL"
            status={postgresDatabase === "unknown" ? "unknown" : "ok"}
            rows={[
              ["Base", postgresDatabase],
              ["Documentos", formatCount(totalDocuments)],
              ["Errores", formatCount(postgresErrors)]
            ]}
          />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <TaskList title="Ultimas tareas de scraping" tasks={latestScrapingTasks} />
          <TaskList title="Ultimas tareas de indexing" tasks={latestIndexingTasks} />
        </div>

        <div className="mt-5 rounded-md border p-4">
          <h3 className="text-sm font-semibold">Documentos por fuente</h3>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {(sources.data?.items ?? []).map((source) => (
              <div key={source.key} className="flex items-center justify-between rounded-md bg-muted/40 px-3 py-2 text-sm">
                <span className="text-muted-foreground">{source.label}</span>
                <span className="font-medium">{formatCount(source.documentCount ?? 0)}</span>
              </div>
            ))}
            {!sources.data?.items?.length ? <p className="text-sm text-muted-foreground">Sin fuentes cargadas.</p> : null}
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Beta privada</h2>
            <p className="text-sm text-muted-foreground">Usuarios beta, feedback, limites y metricas basicas.</p>
          </div>
          <Badge>{textValue(beta.data?.version?.version, "0.1.0-beta")}</Badge>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <MetricCard icon={Users} label="Usuarios beta" value={formatCount(beta.data?.metrics?.betaUsers)} />
          <MetricCard icon={CheckCircle2} label="Aprobados" value={formatCount(beta.data?.metrics?.approvedUsers)} tone="ok" />
          <MetricCard icon={NotebookIcon} label="Workspaces" value={formatCount(beta.data?.metrics?.workspacesCreated)} />
          <MetricCard icon={Save} label="Citas" value={formatCount(beta.data?.metrics?.savedQuotes)} />
          <MetricCard icon={MessageIcon} label="Feedback" value={formatCount(beta.data?.metrics?.feedback)} />
          <MetricCard icon={AlertCircle} label="Errores recientes" value={formatCount(beta.data?.metrics?.recentErrors)} tone={asNumber(beta.data?.metrics?.recentErrors) ? "danger" : "ok"} />
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-semibold">Feedback recibido</h3>
            <div className="mt-3 space-y-3">
              {(beta.data?.feedback ?? []).slice(0, 6).map((item) => (
                <div key={String(item.id)} className="rounded-md bg-muted/40 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{textValue(item.type)}</span>
                    <Badge>{textValue(item.status)}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{truncate(String(item.message ?? ""), 220)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{textValue(item.page)} - {textValue(item.email)}</p>
                </div>
              ))}
              {!beta.data?.feedback?.length ? <EmptyState label="Sin feedback recibido." /> : null}
            </div>
          </div>
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-semibold">Usuarios beta</h3>
            <div className="mt-3 space-y-3">
              {(beta.data?.users ?? []).slice(0, 6).map((item) => (
                <div key={String(item.id)} className="rounded-md bg-muted/40 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{textValue(item.email)}</span>
                    <Badge>{textValue(item.status)}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {textValue(item.studyProfile)} - {textValue(item.preferredLanguage)}
                  </p>
                </div>
              ))}
              {!beta.data?.users?.length ? <EmptyState label="Sin usuarios beta registrados." /> : null}
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Costos IA</h2>
            <p className="text-sm text-muted-foreground">Uso, cache y control de indexacion OpenAI sin exponer claves al frontend.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={pauseIndexing.isPending || indexingPaused}
              onClick={() => pauseIndexing.mutate()}
            >
              <PauseCircle className="h-4 w-4" />
              Pausar indexing
            </Button>
            <Button
              variant="outline"
              disabled={resumeIndexing.isPending || !indexingPaused}
              onClick={() => resumeIndexing.mutate()}
            >
              <PlayCircle className="h-4 w-4" />
              Reanudar
            </Button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <MetricCard icon={DollarSign} label="Costo hoy" value={`$${Number(cost.data?.estimatedCostToday ?? 0).toFixed(4)}`} />
          <MetricCard icon={DollarSign} label="Costo mes" value={`$${Number(cost.data?.estimatedCostThisMonth ?? 0).toFixed(4)}`} />
          <MetricCard icon={Database} label="Tokens hoy" value={formatCount(cost.data?.tokensUsedToday)} />
          <MetricCard icon={Database} label="Tokens mes" value={formatCount(cost.data?.tokensUsedThisMonth)} />
          <MetricCard icon={RefreshCw} label="Cache skips" value={formatCount(cost.data?.cacheHits)} />
          <MetricCard
            icon={AlertCircle}
            label="OpenAI errors"
            value={formatCount(Array.isArray(cost.data?.recentErrors) ? cost.data.recentErrors.length : 0)}
            tone={Array.isArray(cost.data?.recentErrors) && cost.data.recentErrors.length ? "danger" : "ok"}
          />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <HealthPanel
            title="Modo IA"
            status={indexingPaused ? "paused" : "active"}
            rows={[
              ["Modo", cost.data?.mode],
              ["Modelo", cost.data?.model],
              ["Batch", cost.data?.embeddingBatchSize],
              ["Limite diario", formatCount(cost.data?.dailyTokenLimit)]
            ]}
          />
          <HealthPanel
            title="Estimacion indexing"
            status="ready"
            rows={[
              ["Documentos", formatCount(estimate.data?.documentsToIndex)],
              ["Chunks a generar", formatCount(estimate.data?.chunksToEmbed)],
              ["Chunks en cache", formatCount(estimate.data?.cachedChunks)],
              ["Costo estimado", `$${Number(estimate.data?.estimatedCostUsd ?? 0).toFixed(4)}`]
            ]}
          />
          <HealthPanel
            title="Uso registrado"
            status={String((embeddingGenerated as Record<string, unknown> | undefined)?.kind ?? "sin uso")}
            rows={[
              ["Eventos embedding", formatCount((embeddingGenerated as Record<string, unknown> | undefined)?.events)],
              ["Cache entries", formatCount(cost.data?.cacheEntries)],
              ["Estado", indexingPaused ? textValue(indexingState.reason, "pausado") : "activo"],
              ["Restante hoy", formatCount(estimate.data?.remainingDailyTokens)]
            ]}
          />
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold">Errores y reintentos</h2>
            <p className="text-sm text-muted-foreground">Inspeccion de jobs y documentos fallidos derivados de PostgreSQL.</p>
          </div>
          <Badge>{failedJobs.length + failedDocuments.length} errores</Badge>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Jobs fallidos</h3>
            {failedJobs.length ? (
              failedJobs.map((job) => (
                <div key={String(job.id)} className="rounded-md border p-3 text-sm">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="font-medium">{taskLabel(job)}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {textValue(job.status)} - intentos {formatCount(job.attempts)} - {taskTime(job)}
                      </div>
                    </div>
                    <Button size="sm" variant="outline" disabled={retry.isPending} onClick={() => retry.mutate(String(job.id))}>
                      <RotateCcw className="h-4 w-4" />
                      Reintentar
                    </Button>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{truncate(String(job.error ?? firstError(job) ?? "Sin detalle"), 320)}</p>
                </div>
              ))
            ) : (
              <EmptyState label="No hay jobs fallidos." />
            )}
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Documentos fallidos</h3>
            {failedDocuments.length ? (
              failedDocuments.map((document) => (
                <a
                  key={String(document.id)}
                  href={String(document.url ?? "#")}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-md border p-3 text-sm transition hover:bg-muted"
                >
                  <div className="font-medium">{textValue(document.title, "Documento sin titulo")}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {textValue(document.status)} - {textValue(document.sourceType ?? document.source)}
                  </div>
                  {document.error ? <p className="mt-2 text-xs text-muted-foreground">{truncate(String(document.error), 220)}</p> : null}
                </a>
              ))
            ) : (
              <EmptyState label="No hay documentos fallidos." />
            )}
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-semibold">Fuentes doctrinales</h2>
            <p className="text-sm text-muted-foreground">Catalogo auditable con limites por corrida, robots y crawls por fuente.</p>
          </div>
          <Badge>{sourceCatalog.data?.items?.length ?? 0} fuentes</Badge>
        </div>
        <div className="mt-4 grid gap-3">
          {(sourceCatalog.data?.items ?? []).map((source) => {
            const limit = sourceLimits[source.sourceId] ?? source.maxPagesPerRun;
            return (
              <div key={source.id} className="rounded-md border p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Globe2 className="h-4 w-4 text-primary" />
                      <h3 className="font-medium">{source.name}</h3>
                      <Badge>{source.enabled ? "activa" : "pausada"}</Badge>
                      <Badge>{source.sourceType}</Badge>
                    </div>
                    <a className="mt-1 block truncate text-xs text-muted-foreground" href={source.baseUrl} target="_blank" rel="noreferrer">
                      {source.baseUrl}
                    </a>
                    <p className="mt-2 text-xs text-muted-foreground">{source.robotsPolicyNotes ?? "Sin nota de robots registrada."}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>Idioma: {textValue(source.language)}</span>
                      <span>Estrategia: {source.crawlStrategy}</span>
                      <span>Documentos: {formatCount(source.documentCount)}</span>
                      <span>Indexación: {source.indexingMode}</span>
                      <span>Tokens estimados: {formatCount(source.estimatedEmbeddingTokens)}</span>
                      <span>Errores: {formatCount(source.errorCount)}</span>
                      <span>Último rastreo: {source.lastCrawledAt ? new Date(source.lastCrawledAt).toLocaleString() : "sin ejecutar"}</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      Limite
                      <input
                        className="h-8 w-20 rounded-md border bg-background px-2 text-sm text-foreground"
                        type="number"
                        min={1}
                        max={200}
                        value={limit}
                        onChange={(event) =>
                          setSourceLimits((current) => ({ ...current, [source.sourceId]: Number(event.target.value || source.maxPagesPerRun) }))
                        }
                      />
                    </label>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={updateSource.isPending}
                      onClick={() =>
                        updateSource.mutate({
                          sourceId: source.sourceId,
                          payload: { maxPagesPerRun: limit }
                        })
                      }
                    >
                      <Save className="h-4 w-4" />
                      Guardar limite
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={updateSource.isPending}
                      onClick={() =>
                        updateSource.mutate({
                          sourceId: source.sourceId,
                          payload: { enabled: !source.enabled }
                        })
                      }
                    >
                      {source.enabled ? "Pausar" : "Activar"}
                    </Button>
                    <Button
                      size="sm"
                      disabled={crawlSource.isPending || !source.enabled}
                      onClick={() => crawlSource.mutate({ sourceId: source.sourceId, maxPagesPerRun: limit })}
                    >
                      <Play className="h-4 w-4" />
                      Crawl limitado
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
          {!sourceCatalog.data?.items?.length ? <EmptyState label="No hay fuentes configuradas." /> : null}
        </div>
      </Card>

      <Card className="p-5">
        <h2 className="font-semibold">Estado real</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <pre className="overflow-auto rounded-md border bg-muted p-3 text-xs">
            {JSON.stringify(status.data ?? { loading: true }, null, 2)}
          </pre>
          <pre className="overflow-auto rounded-md border bg-muted p-3 text-xs">
            {JSON.stringify(
              {
                ingestion: ingestion.data ?? { loading: true },
                errors: errors.data ?? { loading: true },
                documentsSummary: documentSummary.data ?? { loading: true }
              },
              null,
              2
            )}
          </pre>
        </div>
      </Card>

      <Card className="p-5">
        <h2 className="font-semibold">Pipelines</h2>
        <div className="mt-4 grid gap-3 text-sm text-muted-foreground">
          <div className="rounded-md border p-3">Scraping distribuido - OCR - documentos</div>
          <div className="rounded-md border p-3">Chunking inteligente - OpenAI embeddings - Qdrant</div>
          <div className="rounded-md border p-3">BM25 + semantic search - reranking - grounding</div>
        </div>
      </Card>
    </div>
  );
}

function AdminActions({
  onRefresh,
  onScrape,
  onReindex,
  scraping,
  reindexing
}: {
  onRefresh: () => void;
  onScrape: () => void;
  onReindex: () => void;
  scraping: boolean;
  reindexing: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="outline" onClick={onRefresh}>
        <RefreshCw className="h-4 w-4" />
        Actualizar estado
      </Button>
      <Button onClick={onScrape} disabled={scraping}>
        <Play className="h-4 w-4" />
        Ejecutar scraping
      </Button>
      <Button variant="secondary" onClick={onReindex} disabled={reindexing}>
        <RefreshCw className="h-4 w-4" />
        Reindexar
      </Button>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  tone,
  compact
}: {
  icon: ElementType;
  label: string;
  value: string;
  tone?: "ok" | "danger";
  compact?: boolean;
}) {
  return (
    <Card className="p-5">
      <Icon className={cn("h-5 w-5 text-primary", tone === "danger" && "text-destructive", tone === "ok" && "text-emerald-600")} />
      <div className={cn("mt-4 font-semibold", compact ? "truncate text-lg" : "text-2xl")}>{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </Card>
  );
}

function StatusPanel({ title, items }: { title: string; items: Array<[unknown, unknown]> }) {
  return (
    <div className="rounded-md border p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.length ? (
          items.map(([label, value]) => (
            <div key={String(label)} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{String(label)}</span>
              <span className="font-medium">{formatCount(value)}</span>
            </div>
          ))
        ) : (
          <EmptyState label="Sin datos." />
        )}
      </div>
    </div>
  );
}

function HealthPanel({ title, status, rows }: { title: string; status: string; rows: Array<[string, unknown]> }) {
  const normalized = status.toLowerCase();
  const healthy = ["ok", "healthy", "ready"].includes(normalized) || !["unknown", "error", "failed"].includes(normalized);
  return (
    <div className="rounded-md border p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Badge className={healthy ? "border-emerald-300 text-emerald-700" : "border-amber-300 text-amber-700"}>
          {healthy ? <CheckCircle2 className="mr-1 h-3 w-3" /> : <AlertCircle className="mr-1 h-3 w-3" />}
          {status}
        </Badge>
      </div>
      <div className="mt-3 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="truncate font-medium">{textValue(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TaskList({ title, tasks }: { title: string; tasks: Array<Record<string, unknown>> }) {
  return (
    <div className="rounded-md border p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-3 space-y-3">
        {tasks.length ? (
          tasks.map((task) => (
            <div key={String(task.id)} className="rounded-md bg-muted/40 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{taskLabel(task)}</span>
                <Badge>{textValue(task.status)}</Badge>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {taskTime(task)} - encontrados {formatCount(task.documentsFound)} - creados {formatCount(task.documentsCreated)} -
                actualizados {formatCount(task.documentsUpdated)}
              </div>
              {task.error ? <p className="mt-2 text-xs text-destructive">{truncate(String(task.error), 220)}</p> : null}
            </div>
          ))
        ) : (
          <EmptyState label="Sin tareas recientes." />
        )}
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <p className="text-sm text-muted-foreground">{label}</p>;
}

function firstError(task: Record<string, unknown>) {
  const errors = task.errors;
  return Array.isArray(errors) ? errors[0] : undefined;
}

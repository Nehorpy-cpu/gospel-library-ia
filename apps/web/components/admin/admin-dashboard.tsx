"use client";

import { Activity, Database, FileText, Play, RefreshCw, Search, Server, ShieldCheck, Tags, Users } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";

const metrics = [
  { label: "Documentos", value: "2.4M", icon: FileText },
  { label: "Chunks", value: "38.1M", icon: Database },
  { label: "Qdrant", value: "Healthy", icon: Server },
  { label: "Consultas IA", value: "18.7K", icon: Search },
  { label: "Grounding", value: "96%", icon: ShieldCheck },
  { label: "Workers", value: "24", icon: Activity }
];

function asNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value ?? 0);
}

function formatCount(value: unknown): string {
  return new Intl.NumberFormat("es").format(asNumber(value));
}

function taskLabel(task: Record<string, unknown>) {
  return String(task.type ?? task.job_type ?? task.id ?? "Tarea");
}

export function AdminDashboard() {
  const status = useQuery({ queryKey: ["admin-status"], queryFn: () => ragApi.adminStatus(), refetchInterval: 15000 });
  const ingestion = useQuery({ queryKey: ["ingestion-status"], queryFn: () => ragApi.ingestionStatus(), refetchInterval: 15000 });
  const documentSummary = useQuery({ queryKey: ["documents-summary"], queryFn: () => ragApi.documentsSummary(), refetchInterval: 15000 });
  const documents = useQuery({ queryKey: ["admin-documents"], queryFn: () => ragApi.documents({ limit: 1, offset: 0 }), refetchInterval: 15000 });
  const authors = useQuery({ queryKey: ["admin-authors"], queryFn: () => ragApi.authors(), refetchInterval: 15000 });
  const topics = useQuery({ queryKey: ["admin-topics"], queryFn: () => ragApi.topics(), refetchInterval: 15000 });
  const scrape = useMutation({ mutationFn: () => ragApi.scrape() });
  const reindex = useMutation({ mutationFn: () => ragApi.reindex() });
  const documentStatuses = documentSummary.data?.documents ?? [];
  const totalDocuments = documents.data?.total ?? status.data?.postgres?.documents ?? 0;
  const qdrantVectors = status.data?.qdrant?.vectors ?? 0;
  const latestScrapingTasks = useMemo(() => {
    const fromEndpoint = ingestion.data?.latestScrapingTasks ?? [];
    const fromButton = scrape.data ? [{ id: scrape.data.task_id, type: "scrape", status: "queued" }] : [];
    return [...fromButton, ...fromEndpoint].slice(0, 6);
  }, [ingestion.data, scrape.data]);
  const latestIndexingTasks = useMemo(() => {
    const fromEndpoint = ingestion.data?.latestIndexingTasks ?? [];
    const fromButton = reindex.data ? [{ id: reindex.data.task_id, type: "index", status: "queued" }] : [];
    return [...fromButton, ...fromEndpoint].slice(0, 6);
  }, [ingestion.data, reindex.data]);

  function refreshAll() {
    void status.refetch();
    void ingestion.refetch();
    void documentSummary.refetch();
    void documents.refetch();
    void authors.refetch();
    void topics.refetch();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard admin</h1>
          <p className="text-sm text-muted-foreground">Operacion de ingesta, embeddings, busqueda y RAG.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refreshAll}>
            <RefreshCw className="h-4 w-4" />
            Actualizar estado
          </Button>
          <Button onClick={() => scrape.mutate()} disabled={scrape.isPending}>
            <Play className="h-4 w-4" />
            Ejecutar scraping
          </Button>
          <Button variant="secondary" onClick={() => reindex.mutate()} disabled={reindex.isPending}>
            <RefreshCw className="h-4 w-4" />
            Reindexar
          </Button>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.label} className="p-5">
              <Icon className="h-5 w-5 text-primary" />
              <div className="mt-4 text-2xl font-semibold">{metric.value}</div>
              <div className="text-sm text-muted-foreground">{metric.label}</div>
            </Card>
          );
        })}
      </div>
      <Card className="p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Datos cargados</h2>
            <p className="text-sm text-muted-foreground">Estado actual de documentos, autores, temas, vectores y tareas.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={refreshAll}>
              <RefreshCw className="h-4 w-4" />
              Actualizar estado
            </Button>
            <Button onClick={() => scrape.mutate()} disabled={scrape.isPending}>
              <Play className="h-4 w-4" />
              Ejecutar scraping
            </Button>
            <Button variant="secondary" onClick={() => reindex.mutate()} disabled={reindex.isPending}>
              <RefreshCw className="h-4 w-4" />
              Reindexar
            </Button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-md border p-4">
            <FileText className="h-4 w-4 text-primary" />
            <div className="mt-3 text-2xl font-semibold">{formatCount(totalDocuments)}</div>
            <div className="text-xs text-muted-foreground">Documentos</div>
          </div>
          <div className="rounded-md border p-4">
            <Users className="h-4 w-4 text-primary" />
            <div className="mt-3 text-2xl font-semibold">{formatCount(authors.data?.items?.length ?? 0)}</div>
            <div className="text-xs text-muted-foreground">Autores</div>
          </div>
          <div className="rounded-md border p-4">
            <Tags className="h-4 w-4 text-primary" />
            <div className="mt-3 text-2xl font-semibold">{formatCount(topics.data?.items?.length ?? 0)}</div>
            <div className="text-xs text-muted-foreground">Temas</div>
          </div>
          <div className="rounded-md border p-4">
            <Database className="h-4 w-4 text-primary" />
            <div className="mt-3 text-2xl font-semibold">{formatCount(qdrantVectors)}</div>
            <div className="text-xs text-muted-foreground">Vectores Qdrant</div>
          </div>
          <div className="rounded-md border p-4">
            <Server className="h-4 w-4 text-primary" />
            <div className="mt-3 text-2xl font-semibold">{String(status.data?.qdrant?.status ?? "loading")}</div>
            <div className="text-xs text-muted-foreground">Estado Qdrant</div>
          </div>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-semibold">Documentos por estado</h3>
            <div className="mt-3 space-y-2">
              {documentStatuses.map((item) => (
                <div key={item.status} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{item.status}</span>
                  <span className="font-medium">{formatCount(item.count)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-semibold">Últimas tareas de scraping</h3>
            <div className="mt-3 space-y-2">
              {latestScrapingTasks.length ? (
                latestScrapingTasks.map((task) => (
                  <div key={String(task.id)} className="text-sm">
                    <div className="font-medium">{taskLabel(task)}</div>
                    <div className="text-xs text-muted-foreground">{String(task.status ?? "sin estado")}</div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Sin tareas recientes.</p>
              )}
            </div>
          </div>
          <div className="rounded-md border p-4">
            <h3 className="text-sm font-semibold">Últimas tareas de indexing</h3>
            <div className="mt-3 space-y-2">
              {latestIndexingTasks.length ? (
                latestIndexingTasks.map((task) => (
                  <div key={String(task.id)} className="text-sm">
                    <div className="font-medium">{taskLabel(task)}</div>
                    <div className="text-xs text-muted-foreground">{String(task.status ?? "sin estado")}</div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Sin tareas recientes.</p>
              )}
            </div>
          </div>
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
          <div className="rounded-md border p-3">Scraping distribuido {"→"} OCR {"→"} documentos</div>
          <div className="rounded-md border p-3">Chunking inteligente {"→"} OpenAI embeddings {"→"} Qdrant</div>
          <div className="rounded-md border p-3">BM25 + semantic search {"→"} reranking {"→"} grounding</div>
        </div>
      </Card>
    </div>
  );
}

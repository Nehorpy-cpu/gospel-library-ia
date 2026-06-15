"use client";

import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState } from "react";

import { SpeechCard } from "@/components/library/speech-card";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";
import { mergeSourceOptions } from "@/lib/source-filters";
import type { SpeechCardItem } from "@/types/library";
import type { SearchResult } from "@/types/rag";

function sourceKind(sourceType: string): SpeechCardItem["kind"] {
  if (sourceType.includes("scripture")) return "scripture";
  if (sourceType.includes("manual")) return "manual";
  if (sourceType.includes("pdf")) return "pdf";
  if (sourceType.includes("audio")) return "audio";
  return "speech";
}

function toSpeechCardItem(item: Record<string, unknown>): SpeechCardItem {
  const sourceType = String(item.sourceType ?? "speech");
  return {
    id: String(item.id),
    title: String(item.title ?? "Documento sin titulo"),
    author: String(item.author ?? "Autor desconocido"),
    source: String(item.source ?? sourceType),
    language: String(item.language ?? "es"),
    summary: String(item.excerpt ?? ""),
    year: item.publishedAt
      ? new Date(String(item.publishedAt)).getUTCFullYear().toString()
      : item.createdAt
        ? new Date(String(item.createdAt)).getUTCFullYear().toString()
        : undefined,
    tags: [String(item.status ?? "READY")],
    kind: sourceKind(sourceType)
  };
}

function searchResultToSpeechCardItem(item: SearchResult): SpeechCardItem {
  const sourceType = item.source_key ?? "speech";
  return {
    id: item.document_id,
    title: item.title || "Documento sin titulo",
    author: item.author || "Autor desconocido",
    source: item.source || item.source_key || "Fuente doctrinal",
    language: item.language || "es",
    summary: item.snippet || "Resultado sin extracto disponible.",
    tags: item.tags?.length ? item.tags : ["Coincidencia textual"],
    kind: sourceKind(sourceType)
  };
}

export function LibraryGrid() {
  const [filter, setFilter] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [hideSeed, setHideSeed] = useState(false);
  const deferredFilter = useDeferredValue(filter.trim());
  const isSearching = deferredFilter.length >= 2;
  const sources = useQuery({
    queryKey: ["source-options"],
    queryFn: () => ragApi.sourcesSummary(),
    staleTime: 1000 * 60
  });
  const documents = useQuery({
    queryKey: ["documents", sourceType, hideSeed],
    queryFn: () =>
      ragApi.documents({
        sourceType: sourceType || undefined,
        includeSeed: !hideSeed,
        limit: 100,
        offset: 0
      }),
    enabled: !isSearching,
    staleTime: 1000 * 60
  });
  const search = useQuery({
    queryKey: ["library-text-search", deferredFilter, sourceType, hideSeed],
    queryFn: () =>
      ragApi.search({
        query: deferredFilter,
        filters: {
          source_keys: sourceType ? [sourceType] : undefined,
          include_seed: !hideSeed
        },
        limit: 50,
        use_reranker: false
      }),
    enabled: isSearching,
    staleTime: 1000 * 60
  });
  const items = useMemo(() => {
    if (isSearching) {
      return (search.data?.items ?? search.data?.results ?? []).map(searchResultToSpeechCardItem);
    }
    return documents.data?.items?.map(toSpeechCardItem) ?? [];
  }, [documents.data, isSearching, search.data]);
  const isLoading = isSearching ? search.isLoading : documents.isLoading;
  const isError = isSearching ? search.isError : documents.isError;
  const error = isSearching ? search.error : documents.error;
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Biblioteca</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discursos, PDFs, manuales, escrituras y audios transcritos.
          </p>
        </div>
        <div className="flex flex-col gap-2 md:w-[520px] md:flex-row">
          <Input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Buscar por tema, autor o contenido"
          />
          <select
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value)}
            className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            aria-label="Filtrar por fuente"
          >
            <option value="">Todas las fuentes</option>
            {mergeSourceOptions(sources.data?.items).map((source) => (
              <option key={source.key} value={source.key}>
                {source.label}
                {typeof source.documentCount === "number" ? ` (${source.documentCount})` : ""}
              </option>
            ))}
          </select>
        </div>
      </div>
      <label className="flex w-fit items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={hideSeed}
          onChange={(event) => setHideSeed(event.target.checked)}
          className="h-4 w-4 rounded border-input accent-primary"
        />
        Ocultar contenido seed/test
      </label>

      {filter.trim().length === 1 ? (
        <p className="text-sm text-muted-foreground">Escribe al menos 2 caracteres para buscar en el contenido.</p>
      ) : null}
      {isError ? (
        <p className="rounded-md border border-accent/40 bg-accent/10 p-3 text-sm text-accent">
          {error instanceof Error ? error.message : "No se pudo consultar la biblioteca."}
        </p>
      ) : null}
      {isLoading ? (
        <p className="text-sm text-muted-foreground">
          {isSearching ? "Buscando en documentos..." : "Cargando documentos..."}
        </p>
      ) : null}
      {!isLoading && !isError && items.length === 0 ? (
        <p className="rounded-md border bg-muted/40 p-5 text-sm text-muted-foreground">
          {isSearching ? "No se encontraron resultados." : "La biblioteca todavia no tiene documentos cargados."}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <SpeechCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

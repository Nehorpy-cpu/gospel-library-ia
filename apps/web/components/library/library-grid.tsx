"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";

import { SpeechCard } from "@/components/library/speech-card";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";
import { mergeSourceOptions } from "@/lib/source-filters";
import type { SpeechCardItem } from "@/types/library";

function toSpeechCardItem(item: Record<string, unknown>): SpeechCardItem {
  const sourceType = String(item.sourceType ?? "speech");
  return {
    id: String(item.id),
    title: String(item.title ?? "Documento sin titulo"),
    author: String(item.author ?? "Autor desconocido"),
    source: String(item.source ?? sourceType),
    language: String(item.language ?? "es"),
    summary: String(item.excerpt ?? ""),
    year: item.createdAt ? new Date(String(item.createdAt)).getFullYear().toString() : undefined,
    tags: [String(item.status ?? "READY")],
    kind: sourceType.includes("scripture")
      ? "scripture"
      : sourceType.includes("manual")
        ? "manual"
        : sourceType.includes("pdf")
          ? "pdf"
          : sourceType.includes("audio")
            ? "audio"
            : "speech"
  };
}

export function LibraryGrid() {
  const [filter, setFilter] = useState("");
  const [sourceType, setSourceType] = useState("");
  const sources = useQuery({ queryKey: ["source-options"], queryFn: () => ragApi.sourcesSummary(), staleTime: 1000 * 60 });
  const documents = useQuery({
    queryKey: ["documents", filter, sourceType],
    queryFn: () => ragApi.documents({ search: filter || undefined, sourceType: sourceType || undefined, limit: 100, offset: 0 }),
    staleTime: 1000 * 60
  });
  const items = useMemo(() => {
    return documents.data?.items?.map(toSpeechCardItem) ?? [];
  }, [documents.data]);
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: Math.ceil(items.length / 3),
    getScrollElement: () => parentRef.current,
    estimateSize: () => 265,
    overscan: 5
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Biblioteca</h1>
          <p className="mt-1 text-sm text-muted-foreground">Discursos, PDFs, manuales, escrituras y audios transcritos.</p>
        </div>
        <div className="flex flex-col gap-2 md:w-[520px] md:flex-row">
          <Input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filtrar biblioteca" />
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
      {documents.isError ? <p className="text-sm text-accent">No se pudo cargar la biblioteca real.</p> : null}
      {documents.isLoading ? <p className="text-sm text-muted-foreground">Cargando documentos...</p> : null}
      {!documents.isLoading && !documents.isError && items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay documentos cargados todavía.</p>
      ) : null}
      <div ref={parentRef} className="h-[calc(100vh-170px)] overflow-auto">
        <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
          {virtualizer.getVirtualItems().map((row) => {
            const rowItems = items.slice(row.index * 3, row.index * 3 + 3);
            return (
              <div
                key={row.key}
                style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${row.start}px)` }}
                className="grid gap-4 pb-4 md:grid-cols-2 xl:grid-cols-3"
              >
                {rowItems.map((item) => (
                  <SpeechCard key={item.id} item={item} />
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

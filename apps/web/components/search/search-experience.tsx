"use client";

import { useSearchParams } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { CitationCard } from "@/components/search/citation-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";
import { mergeSourceOptions } from "@/lib/source-filters";
import { useSearch } from "@/hooks/use-rag";

export function SearchExperience() {
  const params = useSearchParams();
  const initial = params.get("q") ?? "";
  const [query, setQuery] = useState(initial);
  const [submitted, setSubmitted] = useState(initial);
  const [sourceType, setSourceType] = useState("");
  const [language, setLanguage] = useState("");
  const [author, setAuthor] = useState("");
  const [topic, setTopic] = useState("");
  const [scriptureRef, setScriptureRef] = useState("");
  const [publishedAfter, setPublishedAfter] = useState("");
  const [publishedBefore, setPublishedBefore] = useState("");
  const sources = useQuery({ queryKey: ["source-options"], queryFn: () => ragApi.sourcesSummary(), staleTime: 1000 * 60 });
  const { data, isLoading, error } = useSearch(
    {
      query: submitted,
      language: language || undefined,
      filters: {
        source_keys: sourceType ? [sourceType] : undefined,
        languages: language ? [language] : undefined,
        authors: author ? [author] : undefined,
        categories: topic ? [topic] : undefined,
        scripture_refs: scriptureRef ? [scriptureRef] : undefined,
        published_after: publishedAfter || undefined,
        published_before: publishedBefore || undefined
      },
      limit: 30
    },
    submitted.length > 0
  );
  const parentRef = useRef<HTMLDivElement>(null);
  const results = data?.results ?? [];
  const rowVirtualizer = useVirtualizer({
    count: results.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 190,
    overscan: 6
  });
  const suggestions = useMemo(() => ["Expiacion", "Convenios", "Alma 32", "Restauracion", "Templo"], []);

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <aside className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Busqueda global</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Busca por titulo, autor, fuente, tema y contenido disponible.
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(query);
          }}
        >
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tema, autor o escritura" />
          <Button size="icon" aria-label="Buscar">
            <Search className="h-4 w-4" />
          </Button>
        </form>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                setSubmitted(suggestion);
              }}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
            >
              {suggestion}
            </button>
          ))}
        </div>
        <div className="space-y-3 rounded-md border p-3">
          <select
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value)}
            className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            aria-label="Fuente"
          >
            <option value="">Todas las fuentes</option>
            {mergeSourceOptions(sources.data?.items).map((source) => (
              <option key={source.key} value={source.key}>
                {source.label}
                {typeof source.documentCount === "number" ? ` (${source.documentCount})` : ""}
              </option>
            ))}
          </select>
          <div className="grid gap-2 sm:grid-cols-2">
            <Input value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="Idioma" />
            <Input value={author} onChange={(event) => setAuthor(event.target.value)} placeholder="Autor" />
            <Input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Tema" />
            <Input
              value={scriptureRef}
              onChange={(event) => setScriptureRef(event.target.value)}
              placeholder="Alma 32:21"
            />
            <Input
              value={publishedAfter}
              onChange={(event) => setPublishedAfter(event.target.value)}
              placeholder="Desde YYYY-MM-DD"
            />
            <Input
              value={publishedBefore}
              onChange={(event) => setPublishedBefore(event.target.value)}
              placeholder="Hasta YYYY-MM-DD"
            />
          </div>
        </div>
      </aside>
      <section className="min-h-[70vh]">
        {isLoading ? <p className="text-sm text-muted-foreground">Buscando fuentes...</p> : null}
        {error ? (
          <p className="text-sm text-accent">
            {error instanceof Error ? error.message : "No se pudo consultar el servicio RAG."}
          </p>
        ) : null}
        {data?.rewritten_query ? (
          <p className="mb-3 text-sm text-muted-foreground">Consulta optimizada: {data.rewritten_query}</p>
        ) : null}
        {data?.warnings?.length ? (
          <div className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-200">
            {data.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}
        {submitted && !isLoading && !error && results.length === 0 ? (
          <p className="rounded-md border bg-muted/40 p-5 text-sm text-muted-foreground">
            No se encontraron resultados.
          </p>
        ) : null}
        <div ref={parentRef} className="h-[calc(100vh-130px)] overflow-auto pr-2">
          <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}>
            {rowVirtualizer.getVirtualItems().map((virtualRow) => (
              <div
                key={virtualRow.key}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${virtualRow.start}px)`
                }}
                className="pb-3"
              >
                <CitationCard item={results[virtualRow.index]} />
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

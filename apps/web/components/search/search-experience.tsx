"use client";

import { useSearchParams } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Search } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { CitationCard } from "@/components/search/citation-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSearch } from "@/hooks/use-rag";

export function SearchExperience() {
  const params = useSearchParams();
  const initial = params.get("q") ?? "";
  const [query, setQuery] = useState(initial);
  const [submitted, setSubmitted] = useState(initial);
  const { data, isLoading, error } = useSearch({ query: submitted, limit: 30 }, submitted.length > 0);
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
          <h1 className="text-2xl font-semibold">Busqueda global IA</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Combina BM25, vectores, filtros y reranking con citas trazables.
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
            {data.warnings[0]}
          </div>
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

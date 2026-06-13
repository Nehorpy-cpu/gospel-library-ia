"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";

type AuthorItem = {
  name?: string;
  slug?: string;
  documentCount?: number;
};

function normalizeAuthor(item: Record<string, unknown>): AuthorItem {
  return {
    name: typeof item.name === "string" ? item.name : "Autor sin nombre",
    slug: typeof item.slug === "string" ? item.slug : undefined,
    documentCount: typeof item.documentCount === "number" ? item.documentCount : 0
  };
}

export function AuthorsIndex() {
  const [query, setQuery] = useState("");
  const authors = useQuery({
    queryKey: ["authors-index"],
    queryFn: () => ragApi.authors({ limit: 100 }),
    staleTime: 1000 * 60
  });

  const items = useMemo(() => {
    const normalized = (authors.data?.items ?? []).map(normalizeAuthor);
    const cleanQuery = query.trim().toLowerCase();
    if (!cleanQuery) return normalized;
    return normalized.filter((item) => item.name?.toLowerCase().includes(cleanQuery));
  }, [authors.data?.items, query]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Autores</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Indice generado desde documentos reales cargados en PostgreSQL.
          </p>
        </div>
        <div className="relative w-full md:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filtrar autores"
          />
        </div>
      </div>

      {authors.isLoading ? (
        <Card className="p-6 text-sm text-muted-foreground">Cargando autores reales...</Card>
      ) : authors.isError ? (
        <Card className="p-6 text-sm text-destructive">No se pudieron cargar los autores.</Card>
      ) : items.length === 0 ? (
        <Card className="p-6 text-sm text-muted-foreground">
          {query.trim() ? "No hay autores para este filtro." : "No hay autores cargados todavía."}
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const slug = item.slug || item.name || "autor";
            return (
              <Link key={`${slug}-${item.documentCount}`} href={`/authors/${encodeURIComponent(slug)}`}>
                <Card className="h-full p-4 transition-colors hover:border-primary/60">
                  <h2 className="line-clamp-2 text-sm font-semibold capitalize">{item.name}</h2>
                  <p className="mt-2 text-xs text-muted-foreground">{item.documentCount ?? 0} documentos</p>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

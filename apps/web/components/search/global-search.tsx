"use client";

import Link from "next/link";
import { Search, X } from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";
import { useUIStore } from "@/stores/ui-store";

export function GlobalSearch() {
  const { searchOpen, setSearchOpen } = useUIStore();
  const [query, setQuery] = useState("");
  const topics = useQuery({
    queryKey: ["global-search-topics"],
    queryFn: () => ragApi.topics(),
    enabled: searchOpen,
    staleTime: 1000 * 60 * 5
  });
  const suggestions = (topics.data?.items ?? [])
    .map((topic) => String(topic.name ?? topic.slug ?? ""))
    .filter(Boolean)
    .slice(0, 7);
  const visible = query ? [query, ...suggestions.filter((item) => item.toLowerCase() !== query.toLowerCase())] : suggestions;

  if (!searchOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 p-4 backdrop-blur">
      <div className="mx-auto mt-10 max-w-3xl rounded-lg border bg-card shadow-soft">
        <div className="flex items-center gap-3 border-b p-4">
          <Search className="h-5 w-5 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por tema, autor, discurso, escritura o pregunta"
            className="border-0 focus:ring-0"
          />
          <Button variant="ghost" size="icon" onClick={() => setSearchOpen(false)} aria-label="Cerrar">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-2 p-4">
          {visible.slice(0, 7).map((item) => (
            <Link
              key={item}
              href={`/search?q=${encodeURIComponent(item)}`}
              onClick={() => setSearchOpen(false)}
              className="rounded-md px-3 py-2 text-sm hover:bg-muted"
            >
              {item}
            </Link>
          ))}
          {!topics.isLoading && visible.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">No hay sugerencias reales cargadas todavia.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

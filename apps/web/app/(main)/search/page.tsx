import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchExperience } from "@/components/search/search-experience";

export const metadata: Metadata = {
  title: "Busqueda IA",
  description: "Busqueda doctrinal hibrida con BM25, semantic search, reranking y citas."
};

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Cargando busqueda...</div>}>
      <SearchExperience />
    </Suspense>
  );
}

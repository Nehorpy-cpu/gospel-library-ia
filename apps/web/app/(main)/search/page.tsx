import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchExperience } from "@/components/search/search-experience";

export const metadata: Metadata = {
  title: "Busqueda IA",
  description: "Búsqueda doctrinal híbrida con BM25, búsqueda semántica, reordenamiento y citas."
};

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Cargando busqueda...</div>}>
      <SearchExperience />
    </Suspense>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { SpeechCard } from "@/components/library/speech-card";
import { ragApi } from "@/lib/api";
import { documentToSpeechCard } from "@/lib/document-mapper";

export function AuthorDocuments({ name }: { name: string }) {
  const documents = useQuery({
    queryKey: ["author-documents", name],
    queryFn: () => ragApi.documents({ search: name, limit: 24 }),
    staleTime: 1000 * 60
  });
  const items = (documents.data?.items ?? [])
    .filter((item) => (item.author ?? "").toLowerCase().includes(name.toLowerCase().slice(0, 8)))
    .map(documentToSpeechCard);

  if (documents.isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando documentos reales del autor...</p>;
  }

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay documentos reales cargados para este autor.</p>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <SpeechCard key={item.id} item={item} />
      ))}
    </div>
  );
}

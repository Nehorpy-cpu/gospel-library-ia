"use client";

import { useQuery } from "@tanstack/react-query";

import { SpeechCard } from "@/components/library/speech-card";
import { ragApi } from "@/lib/api";
import { documentToSpeechCard } from "@/lib/document-mapper";
import { useLibraryStore } from "@/stores/library-store";

export default function FavoritesPage() {
  const favorites = useLibraryStore((state) => state.favorites);
  const documents = useQuery({
    queryKey: ["favorites-documents"],
    queryFn: () => ragApi.documents({ limit: 100 }),
    enabled: favorites.length > 0,
    staleTime: 1000 * 60
  });
  const items = (documents.data?.items ?? []).filter((item) => favorites.includes(item.id)).map(documentToSpeechCard);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Favoritos</h1>
      {items.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {items.map((item) => (
            <SpeechCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          {favorites.length ? "Tus favoritos aun no coinciden con documentos reales cargados." : "Tus favoritos apareceran aqui."}
        </p>
      )}
    </div>
  );
}

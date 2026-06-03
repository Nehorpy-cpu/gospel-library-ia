"use client";

import { SpeechCard } from "@/components/library/speech-card";
import { featuredDocuments } from "@/lib/mock-data";
import { useLibraryStore } from "@/stores/library-store";

export default function FavoritesPage() {
  const favorites = useLibraryStore((state) => state.favorites);
  const items = featuredDocuments.filter((item) => favorites.includes(item.id));
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
        <p className="text-sm text-muted-foreground">Tus favoritos apareceran aqui.</p>
      )}
    </div>
  );
}

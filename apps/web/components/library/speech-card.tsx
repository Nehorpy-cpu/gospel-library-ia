"use client";

import Link from "next/link";
import { BookOpen, FileText, Headphones, Heart, Play, ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn, truncate } from "@/lib/utils";
import { useLibraryStore } from "@/stores/library-store";
import { useUIStore } from "@/stores/ui-store";
import type { SpeechCardItem } from "@/types/library";

const icons = {
  speech: ScrollText,
  scripture: BookOpen,
  manual: BookOpen,
  pdf: FileText,
  audio: Headphones
};

export function SpeechCard({ item, className }: { item: SpeechCardItem; className?: string }) {
  const Icon = icons[item.kind];
  const { favorites, toggleFavorite, pushHistory } = useLibraryStore();
  const { setAudio } = useUIStore();
  const favorite = favorites.includes(item.id);

  return (
    <Card className={cn("group relative min-h-[230px] overflow-hidden transition hover:-translate-y-0.5 hover:shadow-soft", className)}>
      <Link
        href={`/documents/${item.id}`}
        onClick={() => pushHistory(item.id)}
        className="absolute inset-0 z-0 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={`Abrir ${item.title}`}
      />
      <div className="pointer-events-none relative z-10 flex h-full flex-col p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="pointer-events-auto"
            onClick={() => toggleFavorite(item.id)}
            aria-label="Favorito"
          >
            <Heart className={cn("h-4 w-4", favorite && "fill-accent text-accent")} />
          </Button>
        </div>
        <div className="mt-4 block">
          <h3 className="line-clamp-2 text-base font-semibold leading-snug">{item.title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{item.author}</p>
          <p className="mt-3 line-clamp-3 text-sm text-muted-foreground">{truncate(item.summary, 150)}</p>
        </div>
        <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
          {item.tags.slice(0, 3).map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
          <span>{item.source}</span>
          <div className="flex items-center gap-2">
            {item.duration ? (
              <button
                onClick={() => setAudio(true, item.title)}
                className="pointer-events-auto inline-flex items-center gap-1 hover:text-foreground"
              >
                <Play className="h-3 w-3" />
                {item.duration}
              </button>
            ) : null}
            {item.year ? <span>{item.year}</span> : null}
          </div>
        </div>
      </div>
    </Card>
  );
}

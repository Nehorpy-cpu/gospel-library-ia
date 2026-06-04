"use client";

import Link from "next/link";
import { ArrowRight, Bot, Search, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { ContentRow } from "@/components/home/content-row";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";
import { documentToSpeechCard } from "@/lib/document-mapper";
import { useUIStore } from "@/stores/ui-store";

export function HomeExperience() {
  const { setSearchOpen } = useUIStore();
  const documents = useQuery({
    queryKey: ["home-documents"],
    queryFn: () => ragApi.documents({ limit: 12, offset: 0 }),
    staleTime: 1000 * 60
  });
  const topics = useQuery({
    queryKey: ["home-topics"],
    queryFn: () => ragApi.topics(),
    staleTime: 1000 * 60 * 5
  });
  const studyTopics = (topics.data?.items ?? [])
    .map((topic) => String(topic.name ?? topic.slug ?? ""))
    .filter(Boolean)
    .slice(0, 5);
  const speechItems = (documents.data?.items ?? []).map(documentToSpeechCard);

  return (
    <div className="space-y-8">
      <section className="grid min-h-[360px] gap-5 lg:grid-cols-[1.5fr_.8fr]">
        <div className="relative overflow-hidden rounded-lg border bg-secondary text-secondary-foreground">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_15%,rgba(45,212,191,.22),transparent_34%),linear-gradient(135deg,rgba(15,23,42,.12),transparent)]" />
          <div className="relative flex h-full flex-col justify-end p-6 md:p-8">
            <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-md bg-background/10 px-3 py-1 text-sm">
              <Sparkles className="h-4 w-4" />
              RAG doctrinal con citas verificables
            </div>
            <h1 className="max-w-3xl text-3xl font-semibold leading-tight md:text-5xl">
              Gospel Library IA
            </h1>
            <p className="mt-4 max-w-2xl text-base text-secondary-foreground/80">
              Explora discursos, escrituras, PDFs y transcripciones con busqueda hibrida, resumen IA y fuentes trazables.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button variant="accent" onClick={() => setSearchOpen(true)}>
                <Search className="h-4 w-4" />
                Buscar ahora
              </Button>
              <Link
                href="/chat"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-white/20 bg-white/5 px-4 text-sm font-medium text-white hover:bg-white/10"
              >
                <Bot className="h-4 w-4" />
                Chat doctrinal
              </Link>
            </div>
          </div>
        </div>
        <Card className="p-5">
          <h2 className="text-base font-semibold">Continuar estudio</h2>
          <div className="mt-4 grid gap-2">
            {studyTopics.map((topic) => (
              <Link
                key={topic}
                href={`/search?q=${encodeURIComponent(topic)}`}
                className="flex items-center justify-between rounded-md border px-3 py-3 text-sm hover:bg-muted"
              >
                {topic}
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </Link>
            ))}
            {!topics.isLoading && studyTopics.length === 0 ? (
              <p className="rounded-md border px-3 py-3 text-sm text-muted-foreground">
                No hay temas reales cargados todavia.
              </p>
            ) : null}
          </div>
        </Card>
      </section>
      <ContentRow title="Destacados doctrinales" items={speechItems.slice(0, 6)} />
      <ContentRow title="Discursos y fuentes recientes" items={speechItems.slice(6, 12)} />
      {!documents.isLoading && speechItems.length === 0 ? (
        <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
          No hay documentos reales cargados todavia. Ejecuta scraping o ingestion desde Admin.
        </p>
      ) : null}
    </div>
  );
}

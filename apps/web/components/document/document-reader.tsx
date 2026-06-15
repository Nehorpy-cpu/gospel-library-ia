"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, FileText } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";

type DocumentChunk = {
  id: string;
  index: number;
  section_title?: string | null;
  text: string;
};

function textValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item)) : [];
}

function chunksValue(value: unknown): DocumentChunk[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const chunk = item as Record<string, unknown>;
    const text = textValue(chunk.text);
    if (!text) return [];
    return [
      {
        id: String(chunk.id ?? chunk.index ?? text.slice(0, 24)),
        index: Number(chunk.index ?? 0),
        section_title: textValue(chunk.section_title),
        text
      }
    ];
  });
}

function safeExternalUrl(value: unknown): string | null {
  const candidate = textValue(value);
  if (!candidate) return null;
  try {
    const url = new URL(candidate);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function formatDate(value: unknown): string | null {
  const dateValue = textValue(value);
  if (!dateValue) return null;
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("es", { dateStyle: "long" }).format(date);
}

export function DocumentReader({ id }: { id: string }) {
  const document = useQuery({
    queryKey: ["document", id, "with-chunks"],
    queryFn: () => ragApi.document(id, true),
    retry: false
  });

  if (document.isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando documento...</p>;
  }

  if (document.isError) {
    return (
      <Card className="p-6">
        <h1 className="text-xl font-semibold">No se pudo cargar el documento</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {document.error instanceof Error ? document.error.message : "La API devolvio un error inesperado."}
        </p>
      </Card>
    );
  }

  const data = document.data ?? {};
  if (data.not_found === true) {
    return (
      <Card className="p-6">
        <h1 className="text-xl font-semibold">Documento no encontrado</h1>
        <p className="mt-2 text-sm text-muted-foreground">El documento solicitado no existe o ya no esta disponible.</p>
        <Link href="/library" className="mt-4 inline-flex items-center gap-2 text-sm text-primary">
          <ArrowLeft className="h-4 w-4" />
          Volver a la biblioteca
        </Link>
      </Card>
    );
  }

  const title = textValue(data.title) ?? "Documento sin titulo";
  const author = textValue(data.author) ?? "Autor desconocido";
  const source = textValue(data.source) ?? "Fuente no identificada";
  const category = textValue(data.category) ?? textValue(data.type);
  const language = textValue(data.language);
  const status = textValue(data.status);
  const publishedAt = formatDate(data.published_at ?? data.publishedAt);
  const summary = textValue(data.summary) ?? textValue(data.description);
  const fullText = textValue(data.text);
  const tags = stringList(data.tags ?? data.topics);
  const chunks = chunksValue(data.chunks);
  const sourceUrl = safeExternalUrl(data.source_url ?? data.sourceUrl ?? data.canonical_url);
  const metadata = data.metadata && typeof data.metadata === "object" ? (data.metadata as Record<string, unknown>) : {};
  const isSeed =
    metadata.is_seed === true ||
    metadata.is_seed === "true" ||
    metadata.seed_content === true ||
    metadata.seed_content === "true";
  const hasContent = Boolean(fullText || chunks.length);

  return (
    <div className="space-y-5">
      <Link href="/library" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Volver a la biblioteca
      </Link>

      <Card className="p-5 md:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 flex flex-wrap gap-2">
              {status ? <Badge>{status}</Badge> : null}
              {isSeed ? <Badge>Contenido seed/test</Badge> : null}
              {category ? <Badge>{category}</Badge> : null}
              {language ? <Badge>{language.toUpperCase()}</Badge> : null}
            </div>
            <h1 className="text-2xl font-semibold leading-tight md:text-3xl">{title}</h1>
            <p className="mt-3 text-sm text-muted-foreground">
              {author} · {source}
              {publishedAt ? ` · ${publishedAt}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled title="Proximamente">
              Guardar cita
            </Button>
            <Button variant="outline" disabled title="Proximamente">
              Agregar a estudio
            </Button>
            <Button variant="outline" disabled title="Proximamente">
              Usar en discurso
            </Button>
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Abrir fuente original
                <ExternalLink className="h-4 w-4" />
              </a>
            ) : (
              <Button disabled>Fuente no disponible</Button>
            )}
          </div>
        </div>

        {tags.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Badge key={tag}>{tag}</Badge>
            ))}
          </div>
        ) : null}
      </Card>

      {summary ? (
        <Card className="p-5 md:p-7">
          <h2 className="text-lg font-semibold">Resumen</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">{summary}</p>
        </Card>
      ) : null}

      {!hasContent ? (
        <Card className="border-amber-500/40 bg-amber-500/10 p-5">
          <h2 className="font-semibold">Contenido completo no disponible</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Este registro contiene datos bibliograficos, pero todavia no tiene texto ni chunks legibles cargados.
            Puedes consultar la fuente original cuando el enlace este disponible.
          </p>
        </Card>
      ) : null}

      {fullText ? (
        <Card className="p-5 md:p-8">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Contenido del documento</h2>
          </div>
          <article className="mt-5 whitespace-pre-wrap text-base leading-8">{fullText}</article>
        </Card>
      ) : null}

      {!fullText && chunks.length ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">Contenido por secciones</h2>
            <p className="mt-1 text-sm text-muted-foreground">{chunks.length} chunks disponibles para lectura.</p>
          </div>
          {chunks.map((chunk) => (
            <Card key={chunk.id} className="p-5 md:p-7">
              <h3 className="font-semibold">{chunk.section_title || `Seccion ${chunk.index + 1}`}</h3>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">{chunk.text}</p>
            </Card>
          ))}
        </section>
      ) : null}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { PdfReader } from "@/components/document/pdf-reader";
import { ScriptureReferences } from "@/components/document/scripture-references";
import { CitationCard } from "@/components/search/citation-card";
import { SaveToStudyActions } from "@/components/study/save-to-study-actions";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";

export function DocumentReader({ id }: { id: string }) {
  const [selectedText, setSelectedText] = useState("");
  const { data } = useQuery({
    queryKey: ["document", id],
    queryFn: () => ragApi.document(id),
    retry: false
  });
  const title = typeof data?.title === "string" ? data.title : "Documento no encontrado";
  const author = typeof data?.author === "string" && data.author ? data.author : "Autor desconocido";
  const source = typeof data?.canonical_url === "string" ? data.canonical_url : "Fuente no disponible";
  const sourceUrl =
    typeof data?.metadata === "object" && data.metadata && "source_url" in data.metadata
      ? String((data.metadata as Record<string, unknown>).source_url)
      : source;
  const fullText =
    typeof data?.text === "string" && data.text ? data.text : "Este documento real aun no tiene texto extraido disponible.";
  const summary = fullText.slice(0, 420);
  const language = typeof data?.language === "string" ? data.language : null;

  function captureSelection() {
    const value = window.getSelection()?.toString().trim();
    if (value) setSelectedText(value);
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <div onMouseUp={captureSelection} className="space-y-4">
        <PdfReader title={title} />
        <Card className="p-4">
          <h2 className="text-sm font-semibold">Texto del documento</h2>
          <p className="mt-3 max-h-[360px] overflow-auto text-sm leading-7 text-muted-foreground">{fullText}</p>
        </Card>
      </div>
      <aside className="space-y-4">
        <div>
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {author} · {source}
          </p>
        </div>
        <CitationCard
          item={{
            chunk_id: id,
            document_id: id,
            title,
            author,
            source_key: source,
            canonical_url: sourceUrl,
            language,
            section_title: "Resumen IA",
            snippet: summary,
            score: 0.93,
            metadata: {}
          }}
        />
        <SaveToStudyActions
          quote={{
            documentId: id,
            quote: selectedText || summary,
            selectedText: selectedText || undefined,
            citationUrl: sourceUrl,
            location: {
              source: "reader",
              selected: Boolean(selectedText),
              title
            }
          }}
          postIt={{
            documentId: id,
            content: selectedText || `Nota sobre ${title}`,
            color: "yellow",
            position: { x: 24, y: 24 }
          }}
        />
        <ScriptureReferences />
      </aside>
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { featuredDocuments } from "@/lib/mock-data";
import { PdfReader } from "@/components/document/pdf-reader";
import { ScriptureReferences } from "@/components/document/scripture-references";
import { CitationCard } from "@/components/search/citation-card";

export function DocumentReader({ id }: { id: string }) {
  const { data } = useQuery({
    queryKey: ["document", id],
    queryFn: async () => {
      const response = await fetch(`/api/documents/${id}`);
      if (!response.ok) throw new Error("Document not found");
      return response.json() as Promise<Record<string, unknown>>;
    },
    retry: false
  });
  const doc = featuredDocuments.find((item) => item.id === id) ?? featuredDocuments[0];
  const title = typeof data?.title === "string" ? data.title : doc.title;
  const author = typeof data?.author === "string" ? data.author : doc.author;
  const source = typeof data?.canonical_url === "string" ? data.canonical_url : doc.source;
  const summary = typeof data?.text === "string" && data.text ? data.text.slice(0, 420) : doc.summary;
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <PdfReader title={title} />
      <aside className="space-y-4">
        <div>
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {author} · {source}
          </p>
        </div>
        <CitationCard
          item={{
            chunk_id: doc.id,
            document_id: doc.id,
            title,
            author,
            source_key: source,
            canonical_url: "#",
            language: doc.language,
            section_title: "Resumen IA",
            snippet: summary,
            score: 0.93,
            metadata: {}
          }}
        />
        <ScriptureReferences />
      </aside>
    </div>
  );
}

import type { Metadata } from "next";

import { SpeechCard } from "@/components/library/speech-card";
import { featuredDocuments } from "@/lib/mock-data";

export const metadata: Metadata = {
  title: "Autor"
};

export default async function AuthorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const name = decodeURIComponent(slug).replaceAll("-", " ");
  const items = featuredDocuments.filter((item) => item.author.toLowerCase().includes(name.toLowerCase().slice(0, 8)));
  const visible = items.length ? items : featuredDocuments;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold capitalize">{name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Discursos, documentos, citas recuperadas y resumen IA del autor.
        </p>
      </div>
      <section className="rounded-lg border bg-card p-5">
        <h2 className="font-semibold">Resumen IA</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Esta pagina esta preparada para sintetizar temas frecuentes, fuentes principales, cronologia y citas
          verificables del autor usando el servicio RAG.
        </p>
      </section>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {visible.map((item) => (
          <SpeechCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

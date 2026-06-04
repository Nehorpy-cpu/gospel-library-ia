import type { Metadata } from "next";

import { AuthorDocuments } from "@/components/authors/author-documents";

export const metadata: Metadata = {
  title: "Autor"
};

export default async function AuthorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const name = decodeURIComponent(slug).replaceAll("-", " ");

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
      <AuthorDocuments name={name} />
    </div>
  );
}

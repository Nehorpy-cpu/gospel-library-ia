import type { CollectionItem, SpeechCardItem } from "@/types/library";

export const featuredDocuments: SpeechCardItem[] = [
  {
    id: "atonement-byu",
    title: "La Expiacion de Jesucristo",
    author: "Jeffrey R. Holland",
    source: "BYU Speeches",
    language: "es",
    summary: "Una lectura guiada sobre gracia, arrepentimiento y esperanza centrada en Cristo.",
    duration: "42 min",
    year: "2001",
    tags: ["Expiacion", "Cristo", "Fe"],
    kind: "speech"
  },
  {
    id: "covenants-manual",
    title: "Convenios y ordenanzas",
    author: "Manual de la Iglesia",
    source: "Church",
    language: "es",
    summary: "Principios oficiales sobre promesas, autoridad y discipulado.",
    year: "2024",
    tags: ["Convenios", "Templo"],
    kind: "manual"
  },
  {
    id: "jsp-first-vision",
    title: "Relatos de la Primera Vision",
    author: "Joseph Smith Papers",
    source: "JSP",
    language: "en",
    summary: "Documentos historicos con contexto, fechas y referencias primarias.",
    year: "1832",
    tags: ["Restauracion", "Historia"],
    kind: "pdf"
  },
  {
    id: "alma-32",
    title: "Alma 32: Fe como semilla",
    author: "Libro de Mormon",
    source: "Escrituras",
    language: "es",
    summary: "Bloque de estudio con referencias cruzadas y temas relacionados.",
    tags: ["Fe", "Escrituras"],
    kind: "scripture"
  }
];

export const continueStudying = [
  "Plan de Salvacion",
  "Fe y arrepentimiento",
  "Restauracion",
  "Doctrina de Cristo",
  "Sacerdocio",
  "Convenios"
];

export const collections: CollectionItem[] = [
  { id: "lesson", name: "Clase de domingo", description: "Fuentes para preparar lecciones.", count: 18, updatedAt: "Hoy" },
  { id: "talk", name: "Discurso sacramental", description: "Citas sobre fe, Cristo y convenios.", count: 12, updatedAt: "Ayer" },
  { id: "research", name: "Historia de la Restauracion", description: "JSP, discursos y notas.", count: 31, updatedAt: "Esta semana" }
];

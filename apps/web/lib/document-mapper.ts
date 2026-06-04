import type { SpeechCardItem } from "@/types/library";
import type { StudyDocument } from "@/types/study";

export function documentToSpeechCard(document: StudyDocument): SpeechCardItem {
  return {
    id: document.id,
    title: document.title || "Documento sin titulo",
    author: document.author || "Autor desconocido",
    source: document.source || document.sourceType || "Fuente doctrinal",
    language: document.language || "es",
    summary: document.excerpt || "Documento real cargado sin extracto disponible.",
    year: document.createdAt ? new Date(document.createdAt).getFullYear().toString() : undefined,
    tags: [document.sourceType, document.language, document.status].filter(Boolean) as string[],
    kind: sourceTypeToKind(document.sourceType)
  };
}

export function sourceTypeToKind(sourceType?: string | null): SpeechCardItem["kind"] {
  if (!sourceType) return "speech";
  if (sourceType.includes("manual")) return "manual";
  if (sourceType.includes("scripture")) return "scripture";
  if (sourceType.includes("pdf")) return "pdf";
  if (sourceType.includes("audio")) return "audio";
  return "speech";
}

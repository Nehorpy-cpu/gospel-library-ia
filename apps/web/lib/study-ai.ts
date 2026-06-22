import type { StudyBlockType, WorkspaceAiSuggestion } from "@/types/study";

export type EditableWorkspaceAiSuggestion = WorkspaceAiSuggestion & {
  localId: string;
  discarded?: boolean;
  saved?: boolean;
};

export function mapWorkspaceAiTypeToBlockType(type: WorkspaceAiSuggestion["type"]): StudyBlockType {
  if (type === "quote" || type === "manual_reference" || type === "book_reference") {
    return "quote";
  }
  if (type === "reflection_question" || type === "calling_application" || type === "personal_application") {
    return "reflection";
  }
  if (type === "powerful_phrase") {
    return "post_it";
  }
  if (type === "scripture_context" || type === "scripture_connection") {
    return "scripture";
  }
  return "doctrinal_analysis";
}

export function sourceStatusLabel(status: WorkspaceAiSuggestion["source_status"]) {
  if (status === "local") return "Fuente local";
  if (status === "user_private") return "Fuente privada";
  if (status === "suggested") return "Referencia sugerida";
  return "Sin fuente verificada";
}

export function isSuggestedReference(status: WorkspaceAiSuggestion["source_status"]) {
  return status === "suggested" || status === "none";
}

import type { ChatRequest, ChatResponse, ChatStreamEvent, SearchRequest, SearchResponse } from "@/types/rag";
import type {
  SavedStudyCitation,
  StudyDocument,
  StudyHighlight,
  StudyList,
  StudyNote,
  StudyPostIt,
  StudyWorkspace,
  WorkspaceSourceFilter
} from "@/types/study";
import { chatRequestSchema, searchRequestSchema } from "@/lib/validators";
import type { SourceFilterOption } from "@/lib/source-filters";
import type { TalkBuilderOutline, TalkBuilderRequest, TalkDraftResponse } from "@/types/talk-builder";

const API_BASE_URL = process.env.NEXT_PUBLIC_RAG_API_URL ?? "/api";
const MISSING_OPENAI_MESSAGE = "Falta configurar la clave de OpenAI para busqueda IA.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    try {
      const parsed = JSON.parse(detail) as { status?: string };
      if (parsed.status === "missing_api_key") {
        throw new Error(MISSING_OPENAI_MESSAGE);
      }
    } catch (error) {
      if (error instanceof Error && error.message === MISSING_OPENAI_MESSAGE) {
        throw error;
      }
    }
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestFile(path: string, init?: RequestInit): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed: ${response.status}`);
  }
  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = /filename="?([^";]+)"?/i.exec(disposition);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] ?? "gospel-library-export"
  };
}

function studyHeaders(userId: string) {
  return { "X-User-Id": userId };
}

export function downloadBlob({ blob, filename }: { blob: Blob; filename: string }) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const ragApi = {
  search(payload: SearchRequest) {
    const body = searchRequestSchema.parse({
      filters: {},
      limit: 12,
      use_reranker: true,
      ...payload
    });
    return request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },
  chat(payload: ChatRequest) {
    const body = chatRequestSchema.parse({ mode: "doctrinal_assistant", ...payload });
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },
  async streamChat(payload: ChatRequest, onEvent: (event: ChatStreamEvent) => void) {
    const response = await this.chat(payload);
    onEvent({ type: "session", session_id: response.session_id });
    onEvent({ type: "citations", citations: response.citations });
    onEvent({ type: "delta", content: response.message });
    onEvent({ type: "grounding", grounded: response.grounded, warnings: response.warnings });
    onEvent({ type: "done" });
  },
  documents(params?: { search?: string; limit?: number; offset?: number; status?: string; sourceType?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    if (params?.status) searchParams.set("status", params.status);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    const query = searchParams.toString();
    return request<{ items: StudyDocument[]; total?: number; limit?: number; offset?: number }>(
      `/documents${query ? `?${query}` : ""}`
    );
  },
  documentsSummary() {
    return request<{ documents: Array<{ status: string; count: number }> }>("/documents/summary");
  },
  authors() {
    return request<{ items: Array<Record<string, unknown>> }>("/authors");
  },
  topics() {
    return request<{ items: Array<Record<string, unknown>> }>("/topics");
  },
  sourcesSummary() {
    return request<{ items: SourceFilterOption[] }>("/sources/summary");
  },
  adminStatus() {
    return request<{ postgres: Record<string, unknown>; qdrant: Record<string, unknown> }>("/admin/status");
  },
  ingestionStatus() {
    return request<{
      jobs: Array<Record<string, unknown>>;
      documents: Array<Record<string, unknown>>;
      recentJobs?: Array<Record<string, unknown>>;
      latestScrapingTasks?: Array<Record<string, unknown>>;
      latestIndexingTasks?: Array<Record<string, unknown>>;
    }>("/ingestion/status");
  },
  reindex() {
    return request<{ task_id: string }>("/admin/reindex", {
      method: "POST",
      body: JSON.stringify({ limit: 100, force: false })
    });
  },
  scrape() {
    return request<{ task_id: string }>("/admin/scrape", { method: "POST" });
  }
};

export const studyApi = {
  workspaces(userId: string, params?: { sourceType?: string; topic?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    const query = searchParams.toString();
    return request<StudyList<StudyWorkspace>>(`/study-workspaces${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createWorkspace(userId: string, payload: { name: string; description?: string }) {
    return request<StudyWorkspace>("/study-workspaces", {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  updateWorkspace(userId: string, workspaceId: string, payload: { name?: string; description?: string }) {
    return request<StudyWorkspace>(`/study-workspaces/${workspaceId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteWorkspace(userId: string, workspaceId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  sourceFilters(userId: string, workspaceId: string) {
    return request<StudyList<WorkspaceSourceFilter>>(`/study-workspaces/${workspaceId}/sources`, {
      headers: studyHeaders(userId)
    });
  },
  createSourceFilter(
    userId: string,
    workspaceId: string,
    payload: { sourceKey?: string; language?: string; author?: string; category?: string; tags?: string[] }
  ) {
    return request<WorkspaceSourceFilter>(`/study-workspaces/${workspaceId}/sources`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteSourceFilter(userId: string, workspaceId: string, sourceFilterId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}/sources/${sourceFilterId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  notes(
    userId: string,
    workspaceId: string,
    params?: { documentId?: string; sourceType?: string; topic?: string; scriptureRef?: string }
  ) {
    const searchParams = new URLSearchParams();
    if (params?.documentId) searchParams.set("documentId", params.documentId);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    if (params?.scriptureRef) searchParams.set("scriptureRef", params.scriptureRef);
    const query = searchParams.toString();
    return request<StudyList<StudyNote>>(`/study-workspaces/${workspaceId}/notes${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createNote(
    userId: string,
    workspaceId: string,
    payload: { documentId?: string; title?: string; content: string; selectedText?: string; scriptureRefs?: string[] }
  ) {
    return request<StudyNote>(`/study-workspaces/${workspaceId}/notes`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  updateNote(userId: string, workspaceId: string, noteId: string, payload: { title?: string; content?: string }) {
    return request<StudyNote>(`/study-workspaces/${workspaceId}/notes/${noteId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteNote(userId: string, workspaceId: string, noteId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}/notes/${noteId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  highlights(
    userId: string,
    workspaceId: string,
    params?: { documentId?: string; sourceType?: string; topic?: string; scriptureRef?: string }
  ) {
    const searchParams = new URLSearchParams();
    if (params?.documentId) searchParams.set("documentId", params.documentId);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    if (params?.scriptureRef) searchParams.set("scriptureRef", params.scriptureRef);
    const query = searchParams.toString();
    return request<StudyList<StudyHighlight>>(`/study-workspaces/${workspaceId}/highlights${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createHighlight(
    userId: string,
    workspaceId: string,
    payload: { documentId: string; startChar: number; endChar: number; selectedText: string; scriptureRefs?: string[] }
  ) {
    return request<StudyHighlight>(`/study-workspaces/${workspaceId}/highlights`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteHighlight(userId: string, workspaceId: string, highlightId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}/highlights/${highlightId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  citations(
    userId: string,
    workspaceId: string,
    params?: { documentId?: string; sourceType?: string; topic?: string; scriptureRef?: string }
  ) {
    const searchParams = new URLSearchParams();
    if (params?.documentId) searchParams.set("documentId", params.documentId);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    if (params?.scriptureRef) searchParams.set("scriptureRef", params.scriptureRef);
    const query = searchParams.toString();
    return request<StudyList<SavedStudyCitation>>(`/study-workspaces/${workspaceId}/citations${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  saveCitation(
    userId: string,
    workspaceId: string,
    payload: {
      documentId: string;
      quote: string;
      selectedText?: string;
      citationUrl?: string;
      location?: Record<string, unknown>;
      scriptureRefs?: string[];
    }
  ) {
    return request<SavedStudyCitation>(`/study-workspaces/${workspaceId}/citations`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteCitation(userId: string, workspaceId: string, citationId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}/citations/${citationId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  postIts(userId: string, workspaceId: string, params?: { documentId?: string; sourceType?: string; topic?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.documentId) searchParams.set("documentId", params.documentId);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    const query = searchParams.toString();
    return request<StudyList<StudyPostIt>>(`/study-workspaces/${workspaceId}/post-its${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createPostIt(
    userId: string,
    workspaceId: string,
    payload: {
      documentId?: string;
      content: string;
      color?: string;
      position?: Record<string, unknown>;
      pinned?: boolean;
      sourceFilters?: Record<string, unknown>;
    }
  ) {
    return request<StudyPostIt>(`/study-workspaces/${workspaceId}/post-its`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  updatePostIt(
    userId: string,
    workspaceId: string,
    postItId: string,
    payload: {
      documentId?: string;
      content?: string;
      color?: string;
      position?: Record<string, unknown>;
      pinned?: boolean;
      sourceFilters?: Record<string, unknown>;
    }
  ) {
    return request<StudyPostIt>(`/study-workspaces/${workspaceId}/post-its/${postItId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deletePostIt(userId: string, workspaceId: string, postItId: string) {
    return request<{ deleted: boolean }>(`/study-workspaces/${workspaceId}/post-its/${postItId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  }
};

export const talkBuilderApi = {
  outline(userId: string, payload: TalkBuilderRequest) {
    return request<TalkBuilderOutline>("/talk-builder/outline", {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  saveDraft(
    userId: string,
    payload: { title: string; workspaceId?: string; outline: TalkBuilderOutline; content?: string; scriptureRefs?: string[] }
  ) {
    return request<TalkDraftResponse>("/talk-builder/drafts", {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  }
};

export const exportsApi = {
  study(
    userId: string,
    payload: {
      workspaceId: string;
      kind?: "notes" | "quotes" | "talk_drafts" | "all";
      format?: "markdown" | "pdf";
      noteIds?: string[];
      citationIds?: string[];
    }
  ) {
    return requestFile("/exports/study", {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  }
};

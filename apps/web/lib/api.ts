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
import type { CallingFocus } from "@/lib/church-callings";
import { apiFetch } from "@/lib/api-client";

const MISSING_OPENAI_MESSAGE = "Falta configurar la clave de OpenAI para busqueda IA.";

type DocumentListResponse = {
  items?: StudyDocument[];
  documents?: StudyDocument[];
  total?: number;
  limit?: number;
  offset?: number;
};

function readCookie(name: string) {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

function authHeaders(): Record<string, string> {
  const userId = readCookie("gospel_user_id");
  if (!userId) return {};
  return {
    "X-User-Id": userId,
    "X-User-Role": readCookie("gospel_user_role") ?? "user",
    "X-User-Email": readCookie("gospel_user_email") ?? ""
  };
}

function requestHeaders(initHeaders?: HeadersInit) {
  const headers = new Headers(initHeaders);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  for (const [key, value] of Object.entries(authHeaders())) {
    headers.set(key, value);
  }
  return headers;
}

function normalizeSearchResponse(value: unknown): SearchResponse {
  if (!value || typeof value !== "object") {
    throw new Error("Respuesta de búsqueda inválida: se esperaba un objeto.");
  }
  const response = value as Partial<SearchResponse>;
  if (typeof response.query !== "string") {
    throw new Error("Respuesta de búsqueda inválida: falta la consulta.");
  }
  if (response.items !== undefined && !Array.isArray(response.items)) {
    throw new Error("Respuesta de búsqueda inválida: items debe ser una lista.");
  }
  if (response.results !== undefined && !Array.isArray(response.results)) {
    throw new Error("Respuesta de búsqueda inválida: results debe ser una lista.");
  }
  if (response.warnings !== undefined && !Array.isArray(response.warnings)) {
    throw new Error("Respuesta de búsqueda inválida: warnings debe ser una lista.");
  }
  const items = response.items ?? response.results ?? [];
  const results = response.results ?? response.items ?? [];
  return {
    query: response.query,
    rewritten_query: response.rewritten_query ?? null,
    mode: response.mode ?? "postgres_text",
    warnings: response.warnings ?? [],
    items,
    results,
    total: response.total ?? results.length
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, {
    ...init,
    headers: requestHeaders(init?.headers)
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
  const response = await apiFetch(path, {
    ...init,
    headers: requestHeaders(init?.headers)
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
  return { ...authHeaders(), "X-User-Id": userId } satisfies Record<string, string>;
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
  async search(payload: SearchRequest) {
    const body = searchRequestSchema.parse({
      filters: {},
      limit: 12,
      use_reranker: true,
      ...payload
    });
    const response = await request<unknown>("/search", {
      method: "POST",
      body: JSON.stringify(body)
    });
    return normalizeSearchResponse(response);
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
  documents(params?: {
    search?: string;
    limit?: number;
    offset?: number;
    status?: string;
    sourceType?: string;
    includeSeed?: boolean;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    if (params?.status) searchParams.set("status", params.status);
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.includeSeed !== undefined) searchParams.set("includeSeed", String(params.includeSeed));
    const query = searchParams.toString();
    return request<DocumentListResponse>(`/documents${query ? `?${query}` : ""}`).then((response) => ({
      ...response,
      items: response.items ?? response.documents ?? []
    }));
  },
  document(documentId: string, includeChunks = true) {
    const searchParams = new URLSearchParams();
    if (includeChunks) searchParams.set("include_chunks", "true");
    const query = searchParams.toString();
    return request<Record<string, unknown>>(
      `/documents/${encodeURIComponent(documentId)}${query ? `?${query}` : ""}`
    );
  },
  documentsSummary() {
    return request<{ documents: Array<{ status: string; count: number }> }>("/documents/summary");
  },
  authors(params?: { limit?: number; offset?: number; search?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    if (params?.search) searchParams.set("search", params.search);
    const query = searchParams.toString();
    return request<{ items: Array<Record<string, unknown>> }>(`/authors${query ? `?${query}` : ""}`);
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
  adminErrors() {
    return request<{
      jobs: Array<Record<string, unknown>>;
      documents: Array<Record<string, unknown>>;
    }>("/admin/errors");
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
  indexingEstimate(params?: { limit?: number; force?: boolean }) {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.force !== undefined) searchParams.set("force", String(params.force));
    const query = searchParams.toString();
    return request<Record<string, unknown>>(`/admin/indexing/estimate${query ? `?${query}` : ""}`);
  },
  adminCost() {
    return request<Record<string, unknown>>("/admin/cost");
  },
  pauseIndexing() {
    return request<{ state: Record<string, unknown> }>("/admin/indexing/pause", { method: "POST" });
  },
  resumeIndexing() {
    return request<{ state: Record<string, unknown> }>("/admin/indexing/resume", { method: "POST" });
  },
  scrape() {
    return request<{ task_id: string }>("/admin/scrape", { method: "POST" });
  },
  retryJob(jobId: string) {
    return request<{ task_id: string; type: string; status: string }>("/admin/jobs/" + encodeURIComponent(jobId) + "/retry", {
      method: "POST"
    });
  },
  adminSources() {
    return request<{
      items: Array<{
        id: string;
        sourceId: string;
        name: string;
        sourceType: string;
        baseUrl: string;
        language?: string | null;
        enabled: boolean;
        crawlStrategy: string;
        rateLimit: number;
        maxPagesPerRun: number;
        lastCrawledAt?: string | null;
        robotsPolicyNotes?: string | null;
        documentCount: number;
        estimatedEmbeddingTokens: number;
        indexingMode: string;
        latestJobAt?: string | null;
        errorCount: number;
      }>;
    }>("/admin/sources");
  },
  updateAdminSource(sourceId: string, payload: { enabled?: boolean; maxPagesPerRun?: number }) {
    return request<{ id: string; sourceId: string; enabled: boolean; maxPagesPerRun: number }>(
      "/admin/sources/" + encodeURIComponent(sourceId),
      {
        method: "PATCH",
        body: JSON.stringify(payload)
      }
    );
  },
  crawlSource(sourceId: string, payload?: { maxPagesPerRun?: number }) {
    return request<{ task_id: string; sourceId: string; maxPagesPerRun?: number | null }>(
      "/admin/sources/" + encodeURIComponent(sourceId) + "/crawl",
      {
        method: "POST",
        body: JSON.stringify(payload ?? {})
      }
    );
  },
  betaStatus() {
    return request<Record<string, unknown>>("/beta/status");
  },
  betaVersion() {
    return request<Record<string, unknown>>("/beta/version");
  },
  requestBetaAccess(payload: { email: string; name?: string; message?: string }) {
    return request<Record<string, unknown>>("/beta/request-access", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  completeOnboarding(payload: { callingProfile: string; language: string; preferredSources: string[] }) {
    return request<Record<string, unknown>>("/beta/onboarding", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  submitFeedback(payload: { page: string; type: string; message: string; screenshotUrl?: string }) {
    return request<Record<string, unknown>>("/feedback", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  adminBeta() {
    return request<{
      version: Record<string, unknown>;
      limits: Record<string, unknown>;
      users: Array<Record<string, unknown>>;
      feedback: Array<Record<string, unknown>>;
      metrics: Record<string, unknown>;
    }>("/admin/beta");
  },
  approveBetaUser(payload: { email: string; status?: "pending" | "approved" | "rejected"; notes?: string }) {
    return request<Record<string, unknown>>("/admin/beta/approve", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateFeedbackStatus(feedbackId: string, status: "new" | "reviewing" | "resolved" | "closed") {
    return request<Record<string, unknown>>(`/admin/feedback/${encodeURIComponent(feedbackId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
  }
};

export const studyApi = {
  workspaces(userId: string, params?: { sourceType?: string; topic?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.sourceType) searchParams.set("sourceType", params.sourceType);
    if (params?.topic) searchParams.set("topic", params.topic);
    const query = searchParams.toString();
    return request<StudyList<StudyWorkspace>>(`/study/workspaces${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createWorkspace(
    userId: string,
    payload: { name: string; description?: string; sourceFilters?: Record<string, unknown>; settings?: Record<string, unknown> }
  ) {
    return request<StudyWorkspace>("/study/workspaces", {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  updateWorkspace(
    userId: string,
    workspaceId: string,
    payload: { name?: string; description?: string; sourceFilters?: Record<string, unknown>; settings?: Record<string, unknown> }
  ) {
    return request<StudyWorkspace>(`/study/workspaces/${workspaceId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteWorkspace(userId: string, workspaceId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  },
  related(userId: string, workspaceId: string, limit = 12) {
    return request<{
      workspaceId: string;
      mode: string;
      warning?: string | null;
      query: string;
      results: StudyDocument[];
    }>(`/study/workspaces/${workspaceId}/related?limit=${limit}`, {
      headers: studyHeaders(userId)
    });
  },
  sourceFilters(userId: string, workspaceId: string) {
    return request<StudyList<WorkspaceSourceFilter>>(`/study/workspaces/${workspaceId}/source-filters`, {
      headers: studyHeaders(userId)
    });
  },
  createSourceFilter(
    userId: string,
    workspaceId: string,
    payload: { sourceKey?: string; language?: string; author?: string; category?: string; tags?: string[] }
  ) {
    return request<WorkspaceSourceFilter>(`/study/workspaces/${workspaceId}/source-filters`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteSourceFilter(userId: string, workspaceId: string, sourceFilterId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}/source-filters/${sourceFilterId}`, {
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
    return request<StudyList<StudyNote>>(`/study/workspaces/${workspaceId}/notes${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createNote(
    userId: string,
    workspaceId: string,
    payload: { documentId?: string; title?: string; content: string; selectedText?: string; scriptureRefs?: string[] }
  ) {
    return request<StudyNote>(`/study/workspaces/${workspaceId}/notes`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  updateNote(userId: string, workspaceId: string, noteId: string, payload: { title?: string; content?: string }) {
    return request<StudyNote>(`/study/workspaces/${workspaceId}/notes/${noteId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteNote(userId: string, workspaceId: string, noteId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}/notes/${noteId}`, {
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
    return request<StudyList<StudyHighlight>>(`/study/workspaces/${workspaceId}/highlights${query ? `?${query}` : ""}`, {
      headers: studyHeaders(userId)
    });
  },
  createHighlight(
    userId: string,
    workspaceId: string,
    payload: { documentId: string; startChar: number; endChar: number; selectedText: string; scriptureRefs?: string[] }
  ) {
    return request<StudyHighlight>(`/study/workspaces/${workspaceId}/highlights`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteHighlight(userId: string, workspaceId: string, highlightId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}/highlights/${highlightId}`, {
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
    return request<StudyList<SavedStudyCitation>>(`/study/workspaces/${workspaceId}/citations${query ? `?${query}` : ""}`, {
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
    return request<SavedStudyCitation>(`/study/workspaces/${workspaceId}/citations`, {
      method: "POST",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deleteCitation(userId: string, workspaceId: string, citationId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}/citations/${citationId}`, {
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
    return request<StudyList<StudyPostIt>>(`/study/workspaces/${workspaceId}/sticky-notes${query ? `?${query}` : ""}`, {
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
    return request<StudyPostIt>(`/study/workspaces/${workspaceId}/sticky-notes`, {
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
    return request<StudyPostIt>(`/study/workspaces/${workspaceId}/sticky-notes/${postItId}`, {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
    });
  },
  deletePostIt(userId: string, workspaceId: string, postItId: string) {
    return request<{ deleted: boolean }>(`/study/workspaces/${workspaceId}/sticky-notes/${postItId}`, {
      method: "DELETE",
      headers: studyHeaders(userId)
    });
  }
};

export const profileApi = {
  preferences(userId: string) {
    return request<CallingFocus & { userId: string; updatedAt?: string | null }>("/profile/preferences", {
      headers: studyHeaders(userId)
    });
  },
  updatePreferences(userId: string, payload: CallingFocus) {
    return request<CallingFocus & { userId: string; updatedAt?: string | null }>("/profile/preferences", {
      method: "PATCH",
      headers: studyHeaders(userId),
      body: JSON.stringify(payload)
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

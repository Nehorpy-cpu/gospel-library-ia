import type { ChatRequest, ChatResponse, ChatStreamEvent, SearchRequest, SearchResponse } from "@/types/rag";
import { chatRequestSchema, searchRequestSchema } from "@/lib/validators";

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
    return request<{ items: Array<Record<string, unknown>>; total?: number; limit?: number; offset?: number }>(
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

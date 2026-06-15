export type UUID = string;

export type MetadataFilter = {
  source_keys?: string[];
  languages?: string[];
  document_types?: string[];
  authors?: string[];
  categories?: string[];
  tags?: string[];
  scripture_refs?: string[];
  published_after?: string;
  published_before?: string;
  document_ids?: UUID[];
  include_seed?: boolean;
};

export type SearchRequest = {
  query: string;
  filters?: MetadataFilter;
  language?: string;
  limit?: number;
  use_reranker?: boolean;
};

export type SearchResult = {
  chunk_id: UUID;
  document_id: UUID;
  title: string;
  author?: string | null;
  source?: string | null;
  source_key?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  language?: string | null;
  section_title?: string | null;
  snippet: string;
  score: number;
  semantic_score?: number | null;
  bm25_score?: number | null;
  rerank_score?: number | null;
  tags?: string[];
  metadata: Record<string, unknown>;
};

export type SearchResponse = {
  query: string;
  rewritten_query?: string | null;
  mode?: string;
  warnings?: string[];
  items?: SearchResult[];
  results: SearchResult[];
  total?: number;
};

export type Citation = {
  citation_id: number;
  chunk_id: UUID;
  document_id: UUID;
  title: string;
  author?: string | null;
  source_key?: string | null;
  canonical_url?: string | null;
  published_at?: string | null;
  language?: string | null;
  section_title?: string | null;
  quote: string;
  score: number;
};

export type ChatRequest = {
  message: string;
  session_id?: UUID;
  user_id?: UUID;
  mode?: string;
  language?: string;
  filters?: MetadataFilter;
  stream?: boolean;
  calling_focus?: {
    callingCategory?: string;
    callingName?: string;
    customCallingName?: string;
    callingFocusEnabled: boolean;
  };
};

export type ChatResponse = {
  session_id: UUID;
  message: string;
  citations: Citation[];
  grounded: boolean;
  mode?: string;
  warnings: string[];
};

export type ChatStreamEvent =
  | { type: "session"; session_id: UUID }
  | { type: "citations"; citations: Citation[] }
  | { type: "delta"; content: string }
  | { type: "grounding"; grounded: boolean; warnings: string[] }
  | { type: "done" };

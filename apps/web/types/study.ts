export type StudyWorkspace = {
  id: string;
  userId: string;
  name: string;
  title?: string | null;
  scriptureReference?: string | null;
  scriptureText?: string | null;
  personalThought?: string | null;
  topic?: string | null;
  callingContext?: string | null;
  blocks?: StudyBlock[];
  description?: string | null;
  sourceFilters: Record<string, unknown>;
  settings: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type WorkspaceSourceFilter = {
  id: string;
  workspaceId: string;
  userId: string;
  sourceKey?: string | null;
  language?: string | null;
  author?: string | null;
  category?: string | null;
  tags: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudyNote = {
  id: string;
  workspaceId: string;
  userId: string;
  documentId?: string | null;
  chunkId?: string | null;
  title?: string | null;
  content: string;
  selectedText?: string | null;
  selectionRange: Record<string, unknown>;
  scriptureRefs: string[];
  color: string;
  position: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudyHighlight = {
  id: string;
  workspaceId: string;
  userId: string;
  documentId: string;
  chunkId?: string | null;
  noteId?: string | null;
  startChar: number;
  endChar: number;
  selectedText: string;
  scriptureRefs: string[];
  color: string;
  metadata: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type SavedStudyCitation = {
  id: string;
  workspaceId: string;
  userId: string;
  documentId: string;
  chunkId?: string | null;
  quote: string;
  selectedText?: string | null;
  citationUrl?: string | null;
  sourceUrl?: string | null;
  sourceTitle?: string | null;
  sourceAuthor?: string | null;
  sourceType?: string | null;
  sourceName?: string | null;
  location: Record<string, unknown>;
  scriptureRefs: string[];
  metadata: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudyPostIt = {
  id: string;
  workspaceId: string;
  userId: string;
  documentId?: string | null;
  content: string;
  color: string;
  position: Record<string, unknown>;
  sourceFilters: Record<string, unknown>;
  pinned: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudyDocument = {
  id: string;
  title: string;
  author?: string | null;
  source?: string | null;
  sourceType?: string | null;
  language?: string | null;
  status?: string | null;
  url?: string | null;
  excerpt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudyList<T> = {
  items: T[];
};

export type StudyBlockType =
  | "personal_note"
  | "post_it"
  | "scripture"
  | "quote"
  | "reflection"
  | "doctrinal_analysis"
  | "ai_doctrinal_analysis"
  | "ai_quote"
  | "ai_reference"
  | "scripture_connection"
  | "reflection_question"
  | "powerful_phrase"
  | "name_meaning"
  | "calling_application"
  | "manual_reference"
  | "book_reference";

export type StudySourceType =
  | "scripture"
  | "church_manual"
  | "book"
  | "byu_speech"
  | "discourse"
  | "user_private_note"
  | "library_document";

export type StudyProject = {
  id: string;
  userId: string;
  title: string;
  scriptureReference?: string | null;
  scriptureText?: string | null;
  personalThought?: string | null;
  topic?: string | null;
  callingContext?: string | null;
  blocks?: StudyBlock[];
  sources?: StudySource[];
  createdAt?: string | null;
  updatedAt?: string | null;
  archivedAt?: string | null;
};

export type StudyBlock = {
  id: string;
  studyProjectId?: string;
  workspaceId?: string;
  type: StudyBlockType;
  title: string;
  content: string;
  sourceTitle?: string | null;
  sourceAuthor?: string | null;
  sourceUrl?: string | null;
  sourceReference?: string | null;
  quoteText?: string | null;
  isAiGenerated: boolean;
  isSaved: boolean;
  isDeleted: boolean;
  sortOrder: number;
  metadata: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type StudySource = {
  id: string;
  studyProjectId: string;
  sourceType: StudySourceType;
  title: string;
  author?: string | null;
  url?: string | null;
  reference?: string | null;
  notes?: string | null;
  createdAt?: string | null;
};

export type UserPrivateSource = {
  id: string;
  userId: string;
  title: string;
  author?: string | null;
  sourceType: StudySourceType;
  citationText?: string | null;
  personalNote?: string | null;
  tags: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type AiSuggestionMode = "rapido" | "profundo" | "citas" | "manuales" | "nombres" | "llamamiento";

export type AiSuggestedBlock = {
  type: StudyBlockType;
  title: string;
  content: string;
  quoteText?: string | null;
  sourceTitle?: string | null;
  sourceAuthor?: string | null;
  sourceUrl?: string | null;
  sourceReference?: string | null;
  sourceStatus: "local" | "referencia_sugerida" | "idea_relacionada" | "usuario";
  sources: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
};

export type AiSuggestResponse = {
  suggestions: AiSuggestedBlock[];
  cached: boolean;
  mode: AiSuggestionMode;
  warnings: string[];
  localContext: Array<Record<string, unknown>>;
};

export type WorkspaceAiSuggestionMode = "rapido" | "profundo" | "citas" | "manuales" | "nombres" | "llamamiento";

export type WorkspaceAiSuggestionType =
  | "doctrinal_analysis"
  | "scripture_context"
  | "name_meaning"
  | "christ_connection"
  | "scripture_connection"
  | "quote"
  | "manual_reference"
  | "book_reference"
  | "calling_application"
  | "reflection_question"
  | "powerful_phrase"
  | "personal_application";

export type WorkspaceAiSuggestion = {
  type: WorkspaceAiSuggestionType;
  title: string;
  content: string;
  source_title?: string | null;
  source_author?: string | null;
  source_reference?: string | null;
  source_url?: string | null;
  quote_text?: string | null;
  is_ai_generated: boolean;
  confidence: "low" | "medium" | "high";
  source_status: "local" | "suggested" | "user_private" | "none";
};

export type WorkspaceAiSuggestResponse = {
  suggestions: WorkspaceAiSuggestion[];
  sources_used: Array<Record<string, unknown>>;
  warnings: string[];
};

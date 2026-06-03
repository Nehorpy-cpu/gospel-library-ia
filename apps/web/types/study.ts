export type StudyWorkspace = {
  id: string;
  userId: string;
  name: string;
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

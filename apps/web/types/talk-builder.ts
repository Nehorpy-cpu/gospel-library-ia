export type TalkBuilderCitation = {
  id: string;
  type: "document" | "saved_quote";
  documentId?: string | null;
  title: string;
  author?: string | null;
  url?: string | null;
  quote?: string | null;
  snippet?: string | null;
  scriptureRefs: string[];
};

export type TalkBuilderSection = {
  id: string;
  title: string;
  purpose: string;
  talkingPoints: string[];
  suggestedQuote?: string | null;
  citations: TalkBuilderCitation[];
};

export type TalkBuilderSource = {
  id: string;
  title: string;
  author?: string | null;
  language?: string | null;
  sourceUrl?: string | null;
  canonicalUrl?: string | null;
  sourceType?: string | null;
  sourceName?: string | null;
  excerpt?: string | null;
  scriptureRefs: string[];
};

export type TalkBuilderSavedQuote = {
  id: string;
  workspaceId: string;
  documentId: string;
  quote: string;
  selectedText?: string | null;
  citationUrl?: string | null;
  sourceUrl?: string | null;
  sourceTitle?: string | null;
  sourceAuthor?: string | null;
  scriptureRefs: string[];
};

export type TalkBuilderOutline = {
  status: "ready" | "unavailable";
  mode: "textual_fallback";
  title: string;
  audience: string;
  durationMinutes: number;
  sections: TalkBuilderSection[];
  sources: TalkBuilderSource[];
  savedQuotes: TalkBuilderSavedQuote[];
  scriptureRefs: string[];
  warnings: string[];
};

export type TalkBuilderRequest = {
  topic: string;
  audience: string;
  durationMinutes: number;
  language?: string;
  workspaceId?: string;
  scriptureRefs?: string[];
  sourceTypes?: string[];
};

export type TalkDraftResponse = {
  status: "saved";
  draftId: string;
  workspaceId: string;
  title: string;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type SpeechCardItem = {
  id: string;
  title: string;
  author: string;
  source: string;
  language: string;
  summary: string;
  duration?: string;
  year?: string;
  tags: string[];
  kind: "speech" | "scripture" | "manual" | "pdf" | "audio";
};

export type CollectionItem = {
  id: string;
  name: string;
  description: string;
  count: number;
  updatedAt: string;
};

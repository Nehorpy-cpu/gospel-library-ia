import { z } from "zod";

export const metadataFilterSchema = z.object({
  source_keys: z.array(z.string()).optional(),
  languages: z.array(z.string()).optional(),
  authors: z.array(z.string()).optional(),
  categories: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  published_after: z.string().optional(),
  published_before: z.string().optional(),
  document_ids: z.array(z.string()).optional()
});

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(1000),
  filters: metadataFilterSchema.default({}),
  language: z.string().max(16).optional(),
  limit: z.number().min(1).max(50).default(12),
  use_reranker: z.boolean().default(true)
});

export const chatRequestSchema = z.object({
  message: z.string().min(1).max(8000),
  session_id: z.string().optional(),
  mode: z.string().default("doctrinal_assistant"),
  language: z.string().max(16).optional(),
  filters: metadataFilterSchema.default({})
});

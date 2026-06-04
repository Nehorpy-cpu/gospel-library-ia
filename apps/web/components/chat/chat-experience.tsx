"use client";

import { Send, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useState } from "react";

import { CitationCard } from "@/components/search/citation-card";
import { SaveToStudyActions } from "@/components/study/save-to-study-actions";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";
import type { Citation, UUID } from "@/types/rag";

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  grounded?: boolean;
  warnings?: string[];
};

export function ChatExperience() {
  const [sessionId, setSessionId] = useState<UUID | undefined>();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Puedo ayudarte a estudiar doctrina con fuentes verificables. Haz una pregunta y citare los documentos recuperados."
    }
  ]);
  const [streaming, setStreaming] = useState(false);

  async function submit() {
    const message = input.trim();
    if (!message || streaming) return;
    setInput("");
    setStreaming(true);
    setMessages((current) => [...current, { role: "user", content: message }, { role: "assistant", content: "" }]);
    const citationBuffer: Citation[] = [];
    try {
      await ragApi.streamChat({ message, session_id: sessionId }, (event) => {
        if (event.type === "session") setSessionId(event.session_id);
        if (event.type === "citations") citationBuffer.splice(0, citationBuffer.length, ...event.citations);
        if (event.type === "delta") {
          setMessages((current) => {
            const next = [...current];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + event.content };
            return next;
          });
        }
        if (event.type === "grounding") {
          setMessages((current) => {
            const next = [...current];
            const last = next[next.length - 1];
              next[next.length - 1] = {
                ...last,
                grounded: event.grounded,
                citations: [...citationBuffer],
                warnings: event.warnings
              };
            return next;
          });
        }
      });
    } catch (error) {
      setMessages((current) => {
        const next = [...current];
        next[next.length - 1] = {
          role: "assistant",
          content:
            error instanceof Error
              ? error.message
              : "No pude conectar con el servicio RAG. Verifica que `rag-api` este activo."
        };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="grid h-[calc(100vh-105px)] gap-5 lg:grid-cols-[1fr_420px]">
      <section className="flex min-h-0 flex-col rounded-lg border bg-card">
        <div className="border-b p-4">
          <h1 className="text-xl font-semibold">Chat doctrinal</h1>
          <p className="text-sm text-muted-foreground">Streaming RAG, memoria conversacional y citas verificables.</p>
        </div>
        <div className="min-h-0 flex-1 space-y-4 overflow-auto p-4">
          {messages.map((message, index) => (
            <div key={index} className={message.role === "user" ? "ml-auto max-w-2xl" : "mr-auto max-w-3xl"}>
              <div
                className={
                  message.role === "user"
                    ? "rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground"
                    : "rounded-lg border bg-background px-4 py-3 text-sm"
                }
              >
                <ReactMarkdown className="prose prose-sm max-w-none dark:prose-invert">
                  {message.content || "Pensando..."}
                </ReactMarkdown>
                {message.grounded ? (
                  <div className="mt-3 inline-flex items-center gap-2 text-xs text-primary">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Respuesta fundamentada
                  </div>
                ) : null}
                {message.warnings?.length ? (
                  <div className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-200">
                    {message.warnings.map((warning) => (
                      <p key={warning}>{warning}</p>
                    ))}
                  </div>
                ) : null}
                {message.citations?.length ? (
                  <div className="mt-3 space-y-2 lg:hidden">
                    {message.citations.slice(0, 3).map((citation) => (
                      <SaveToStudyActions
                        key={`${citation.chunk_id}-${citation.citation_id}-inline`}
                        compact
                        quote={{
                          documentId: citation.document_id,
                          quote: citation.quote,
                          selectedText: citation.quote,
                          citationUrl: citation.canonical_url ?? undefined,
                          location: {
                            source: "chat",
                            citationId: citation.citation_id,
                            chunkId: citation.chunk_id,
                            sectionTitle: citation.section_title
                          }
                        }}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
        <form
          className="flex gap-2 border-t p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Pregunta sobre doctrina, escrituras, discursos o una fuente especifica"
          />
          <Button size="icon" disabled={streaming} aria-label="Enviar">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </section>
      <aside className="hidden min-h-0 overflow-auto lg:block">
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">Citas recuperadas</h2>
        <div className="space-y-3">
          {messages
            .flatMap((message) => message.citations ?? [])
            .slice(-8)
            .map((citation) => (
              <div key={`${citation.chunk_id}-${citation.citation_id}`} className="space-y-2">
                <CitationCard item={citation} />
                <SaveToStudyActions
                  compact
                  quote={{
                    documentId: citation.document_id,
                    quote: citation.quote,
                    selectedText: citation.quote,
                    citationUrl: citation.canonical_url ?? undefined,
                    location: {
                      source: "chat",
                      citationId: citation.citation_id,
                      chunkId: citation.chunk_id,
                      sectionTitle: citation.section_title
                    }
                  }}
                />
              </div>
            ))}
        </div>
      </aside>
    </div>
  );
}

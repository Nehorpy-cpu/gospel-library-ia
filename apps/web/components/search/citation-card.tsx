import { ExternalLink } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatScore } from "@/lib/utils";
import type { Citation, SearchResult } from "@/types/rag";

type Props = {
  item: SearchResult | Citation;
};

export function CitationCard({ item }: Props) {
  const quote = "snippet" in item ? item.snippet : item.quote;
  const score = "score" in item ? item.score : 0;
  const source = "source" in item && item.source ? item.source : item.source_key ?? "Fuente";
  const sourceUrl = "source_url" in item && item.source_url ? item.source_url : item.canonical_url;
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold leading-snug">
            <Link href={`/documents/${item.document_id}`} className="hover:text-primary hover:underline">
              {item.title}
            </Link>
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {item.author ?? "Autor desconocido"} · {source}
          </p>
        </div>
        <Badge>{formatScore(score)}</Badge>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{quote}</p>
      {sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex items-center gap-2 text-sm text-primary"
        >
          Ver fuente
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ) : null}
    </Card>
  );
}

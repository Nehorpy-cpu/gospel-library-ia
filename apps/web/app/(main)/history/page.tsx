"use client";

import Link from "next/link";
import { Clock } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";
import { useLibraryStore } from "@/stores/library-store";

export default function HistoryPage() {
  const history = useLibraryStore((state) => state.history);
  const documents = useQuery({
    queryKey: ["history-documents"],
    queryFn: () => ragApi.documents({ limit: 100 }),
    enabled: history.length > 0,
    staleTime: 1000 * 60
  });
  const byId = new Map((documents.data?.items ?? []).map((item) => [item.id, item]));

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Historial</h1>
      <div className="space-y-3">
        {history.length ? (
          history.map((id) => {
            const doc = byId.get(id);
            return (
              <Link key={id} href={`/documents/${id}`}>
                <Card className="flex items-center gap-3 p-4 hover:bg-muted">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <h2 className="text-sm font-medium">{doc?.title ?? "Documento real no cargado"}</h2>
                    <p className="text-xs text-muted-foreground">{doc?.author ?? "Sin metadata disponible"}</p>
                  </div>
                </Card>
              </Link>
            );
          })
        ) : (
          <p className="text-sm text-muted-foreground">Aun no hay lecturas recientes.</p>
        )}
      </div>
    </div>
  );
}

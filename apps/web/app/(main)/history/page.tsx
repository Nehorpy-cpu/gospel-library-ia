"use client";

import Link from "next/link";
import { Clock } from "lucide-react";

import { Card } from "@/components/ui/card";
import { featuredDocuments } from "@/lib/mock-data";
import { useLibraryStore } from "@/stores/library-store";

export default function HistoryPage() {
  const history = useLibraryStore((state) => state.history);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Historial</h1>
      <div className="space-y-3">
        {history.length ? (
          history.map((id) => {
            const doc = featuredDocuments.find((item) => id.startsWith(item.id)) ?? featuredDocuments[0];
            return (
              <Link key={id} href={`/documents/${id}`}>
                <Card className="flex items-center gap-3 p-4 hover:bg-muted">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <h2 className="text-sm font-medium">{doc.title}</h2>
                    <p className="text-xs text-muted-foreground">{doc.author}</p>
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

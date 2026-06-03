import type { Metadata } from "next";
import { BookOpen, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { collections } from "@/lib/mock-data";

export const metadata: Metadata = { title: "Colecciones" };

export default function CollectionsPage() {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Colecciones</h1>
          <p className="text-sm text-muted-foreground">Organiza documentos, notas y citas por estudio.</p>
        </div>
        <Button>
          <Plus className="h-4 w-4" />
          Nueva
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {collections.map((collection) => (
          <Card key={collection.id} className="p-5">
            <BookOpen className="h-5 w-5 text-primary" />
            <h2 className="mt-4 font-semibold">{collection.name}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{collection.description}</p>
            <p className="mt-5 text-sm text-muted-foreground">
              {collection.count} fuentes · {collection.updatedAt}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}

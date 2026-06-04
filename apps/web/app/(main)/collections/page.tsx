import type { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Colecciones" };

export default function CollectionsPage() {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Colecciones</h1>
          <p className="text-sm text-muted-foreground">Organiza documentos, notas y citas por estudio.</p>
        </div>
        <Link href="/study/new">
          <Button>
            <Plus className="h-4 w-4" />
            Nueva
          </Button>
        </Link>
      </div>
      <Card className="p-6">
        <h2 className="font-semibold">Colecciones personales</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Las colecciones se gestionan como espacios de estudio reales. Crea un workspace para agrupar documentos,
          notas, citas y post-it sin usar datos simulados.
        </p>
      </Card>
    </div>
  );
}

import Link from "next/link";
import { BookMarked } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const refs = ["Alma 32:21", "2 Nefi 2:25", "DyC 19:16-19", "Juan 3:16"];

export function ScriptureReferences() {
  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2">
        <BookMarked className="h-4 w-4 text-primary" />
        <h2 className="text-sm font-semibold">Referencias escriturales</h2>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {refs.map((ref) => (
          <Link key={ref} href={`/search?q=${encodeURIComponent(ref)}`}>
            <Badge className="hover:bg-muted">{ref}</Badge>
          </Link>
        ))}
      </div>
    </section>
  );
}

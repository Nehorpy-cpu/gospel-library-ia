import type { SpeechCardItem } from "@/types/library";
import { SpeechCard } from "@/components/library/speech-card";

export function ContentRow({ title, items }: { title: string; items: SpeechCardItem[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="no-scrollbar flex gap-4 overflow-x-auto pb-2">
        {items.map((item) => (
          <SpeechCard key={item.id} item={item} className="w-[280px] shrink-0" />
        ))}
      </div>
    </section>
  );
}

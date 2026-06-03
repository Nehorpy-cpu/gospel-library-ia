export type SourceFilterOption = {
  key: string;
  label: string;
  documentCount?: number;
  canonical?: boolean;
  aliases?: string[];
};

export const canonicalSourceOptions: SourceFilterOption[] = [
  { key: "byu_speeches_es", label: "BYU Speeches ES" },
  { key: "byu_speeches_en", label: "BYU Speeches EN" },
  { key: "discursos_sud", label: "Discursos SUD" },
  { key: "general_conference", label: "Conferencia General" },
  { key: "church_manuals", label: "Manuales de la Iglesia" },
  { key: "joseph_smith_papers", label: "Joseph Smith Papers" },
  { key: "byu_rsc", label: "BYU Religious Studies Center" }
];

export function mergeSourceOptions(items?: SourceFilterOption[]): SourceFilterOption[] {
  if (!items?.length) {
    return canonicalSourceOptions;
  }
  const byKey = new Map(canonicalSourceOptions.map((item) => [item.key, item]));
  for (const item of items) {
    byKey.set(item.key, { ...byKey.get(item.key), ...item });
  }
  return Array.from(byKey.values()).sort((a, b) => a.label.localeCompare(b.label));
}

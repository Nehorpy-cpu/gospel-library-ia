const item = $json;
if (item.status !== "ready") {
  return [{ json: item }];
}

const host = new URL(item.source_url).hostname.replace(/^www\./, "");
const fuentes = {
  "discursosud.com": "Discursos SUD",
  "speeches.byu.edu": "BYU Speeches Español",
  "churchofjesuschrist.org": "Sitio oficial de la Iglesia"
};
const etiquetasBase = {
  "discursosud.com": ["Discursos SUD", "Doctrina"],
  "speeches.byu.edu": ["BYU Speeches", "Devocional"],
  "churchofjesuschrist.org": ["Iglesia de Jesucristo", "Fuente oficial"]
};

const payload = {
  title: item.title,
  author: item.author ?? null,
  source_name: item.source_name ?? fuentes[host] ?? host,
  source_url: item.source_url,
  canonical_url: item.canonical_url ?? item.source_url,
  language: "es",
  content_type: item.content_type ?? "text/html",
  published_at: item.published_at ?? null,
  content: item.content,
  summary: item.summary ?? null,
  tags: [...new Set([...(item.tags ?? []), ...(etiquetasBase[host] ?? [])])],
  metadata: {
    ingestion_mode: "n8n_curated_v1",
    is_seed: false,
    ingested_by: "n8n",
    storage_used: false,
    source_site: host,
    extracted_at: item.extracted_at ?? new Date().toISOString(),
    extractor_version: item.extractor_version ?? "n8n-html-regex-v1"
  }
};

return [{ json: { ...item, payload } }];

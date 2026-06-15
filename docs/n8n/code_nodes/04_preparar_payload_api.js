const item = $json;
if (item.status !== "ready") {
  return [{ json: item }];
}

function normalizarTextoEspanol(value, conservarSaltos = false) {
  let texto = String(value ?? "").replace(/&nbsp;|&#160;/gi, " ");
  const cp1252 = { "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85, "†": 0x86, "‡": 0x87, "ˆ": 0x88, "‰": 0x89, "Š": 0x8a, "‹": 0x8b, "Œ": 0x8c, "Ž": 0x8e, "‘": 0x91, "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97, "˜": 0x98, "™": 0x99, "š": 0x9a, "›": 0x9b, "œ": 0x9c, "ž": 0x9e, "Ÿ": 0x9f };
  for (let intento = 0; intento < 3 && /Ã|Â|â€|â€™|â€œ|â€�/.test(texto); intento += 1) {
    if ([...texto].some((caracter) => caracter.codePointAt(0) > 255 && cp1252[caracter] === undefined)) break;
    try {
      const bytes = Uint8Array.from([...texto], (caracter) => cp1252[caracter] ?? caracter.charCodeAt(0));
      const reparado = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      if (reparado === texto) break;
      texto = reparado;
    } catch {
      break;
    }
  }
  texto = texto.replace(/\u00a0/g, " ").replace(/\u200b/g, "").replace(/Â(?=\s|$)/g, "").normalize("NFC");
  return conservarSaltos
    ? texto.split(/\r?\n/).map((linea) => linea.replace(/[^\S\n]+/g, " ").trim()).join("\n").replace(/\n{3,}/g, "\n\n").trim()
    : texto.replace(/\s+/g, " ").trim();
}

const traducciones = {
  "atonement": "Expiación",
  "book of mormon": "Libro de Mormón",
  "covenants": "Convenios",
  "faith": "Fe",
  "gospel": "Evangelio",
  "holy ghost": "Espíritu Santo",
  "jesus christ": "Jesucristo",
  "prayer": "Oración",
  "repentance": "Arrepentimiento",
  "temple": "Templo"
};
const normalizarEtiqueta = (tag) => {
  const limpia = normalizarTextoEspanol(tag);
  return traducciones[limpia.toLowerCase()] ?? limpia;
};

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
  title: normalizarTextoEspanol(item.title),
  author: normalizarTextoEspanol(item.author) || null,
  source_name: normalizarTextoEspanol(item.source_name ?? fuentes[host] ?? host),
  source_url: item.source_url,
  canonical_url: item.canonical_url ?? item.source_url,
  language: "es",
  content_type: item.content_type ?? "text/html",
  published_at: item.published_at ?? null,
  content: normalizarTextoEspanol(item.content, true),
  summary: normalizarTextoEspanol(item.summary, true) || null,
  tags: [...new Set([...(item.tags ?? []), ...(etiquetasBase[host] ?? [])].map(normalizarEtiqueta).filter(Boolean))],
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

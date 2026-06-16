const item = $json;

function skipped(razon) {
  return [{
    json: {
      ...item,
      status: "skipped",
      razon
    }
  }];
}

if (item.status !== "ready") {
  return [{ json: item }];
}

function obtenerHost(url) {
  const match = String(url || "").match(/^https:\/\/(?:www\.)?([^\/?#]+)/i);
  return match ? match[1].toLowerCase() : "";
}

function obtenerPath(url) {
  const match = String(url || "").match(/^https:\/\/(?:www\.)?[^\/?#]+([^?#]*)/i);
  return match ? match[1] || "/" : "";
}

function obtenerLang(url) {
  const match = String(url || "").match(/[?&]lang=([^&#]+)/i);
  return match ? decodeURIComponent(match[1]).toLowerCase() : "";
}

function normalizarTexto(value, conservarSaltos = false) {
  const texto = String(value || "")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/\u00a0/g, " ")
    .replace(/\u200b/g, "")
    .normalize("NFC");
  return conservarSaltos
    ? texto.split(/\r?\n/).map((linea) => linea.replace(/[^\S\n]+/g, " ").trim()).filter(Boolean).join("\n").replace(/\n{3,}/g, "\n\n").trim()
    : texto.replace(/\s+/g, " ").trim();
}

function normalizarEtiqueta(tag) {
  const limpia = normalizarTexto(tag);
  const traducciones = {
    "atonement": "Expiacion",
    "book of mormon": "Libro de Mormon",
    "covenants": "Convenios",
    "faith": "Fe",
    "gospel": "Evangelio",
    "holy ghost": "Espiritu Santo",
    "jesus christ": "Jesucristo",
    "prayer": "Oracion",
    "repentance": "Arrepentimiento",
    "temple": "Templo"
  };
  return traducciones[limpia.toLowerCase()] || limpia;
}

const sourceUrl = String(item.source_url || "");
let canonicalUrl = String(item.canonical_url || sourceUrl);
const host = obtenerHost(sourceUrl);
const canonicalHost = obtenerHost(canonicalUrl);
const lang = obtenerLang(sourceUrl);
const canonicalLang = obtenerLang(canonicalUrl);
const path = obtenerPath(sourceUrl);
const idiomasNoEspanoles = new Set(["eng", "por", "fra", "ita", "deu"]);
const hostsPermitidos = new Set(["churchofjesuschrist.org", "discursosud.com", "speeches.byu.edu"]);

if (!sourceUrl || !host) {
  return skipped("La URL de origen no es valida.");
}

if (!hostsPermitidos.has(host)) {
  return skipped("La fuente no esta autorizada para esta ingesta.");
}

if (canonicalHost && !hostsPermitidos.has(canonicalHost)) {
  return skipped("La URL canonica no pertenece a una fuente autorizada.");
}

if (idiomasNoEspanoles.has(lang) || idiomasNoEspanoles.has(canonicalLang)) {
  return skipped("La URL declara un idioma no espanol.");
}

if (host === "churchofjesuschrist.org" && lang !== "spa") {
  return skipped("El sitio oficial de la Iglesia debe declarar lang=spa.");
}

if (canonicalHost === "churchofjesuschrist.org" && canonicalLang && canonicalLang !== "spa") {
  return skipped("La URL canonica oficial debe declarar lang=spa.");
}

if (canonicalHost === "churchofjesuschrist.org" && !canonicalLang) {
  canonicalUrl = sourceUrl;
}

if (host === "speeches.byu.edu" && !path.startsWith("/spa/")) {
  return skipped("BYU Speeches solo se acepta en espanol bajo /spa/.");
}

const fuentes = {
  "discursosud.com": "Discursos SUD",
  "speeches.byu.edu": "BYU Speeches Espanol",
  "churchofjesuschrist.org": "Sitio oficial de la Iglesia"
};

const etiquetasBase = {
  "discursosud.com": ["Discursos SUD", "Doctrina"],
  "speeches.byu.edu": ["BYU Speeches", "Devocional"],
  "churchofjesuschrist.org": ["Iglesia de Jesucristo", "Fuente oficial"]
};

const title = normalizarTexto(item.title);
const content = normalizarTexto(item.content, true);

if (!title || title.length < 3) {
  return skipped("No se pudo preparar un titulo confiable.");
}

if (!content || content.length < 300) {
  return skipped("El contenido limpio es insuficiente para enviar a la API.");
}

const tags = [
  ...new Set([...(item.tags || []), ...(etiquetasBase[host] || [])].map(normalizarEtiqueta).filter(Boolean))
];

return [{
  json: {
    status: "ready",
    title,
    author: normalizarTexto(item.author) || null,
    source_name: normalizarTexto(item.source_name || fuentes[host] || host),
    source_url: sourceUrl,
    canonical_url: canonicalUrl,
    language: "es",
    content_type: item.content_type || "text/html",
    published_at: item.published_at || null,
    content,
    summary: normalizarTexto(item.summary, true) || null,
    tags,
    metadata: {
      ingestion_mode: "n8n_curated_v1",
      is_seed: false,
      ingested_by: "n8n",
      storage_used: false,
      source_site: host,
      extracted_at: item.extracted_at || new Date().toISOString(),
      extractor_version: item.extractor_version || "n8n-html-regex-v2",
      original_content_type: item.content_type || null,
      http_status: item.http_status || null
    }
  }
}];

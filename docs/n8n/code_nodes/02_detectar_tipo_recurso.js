const entrada = $("Procesar una URL por vez").item.json;
const respuesta = $json;

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

function omitido(razon, extra = {}) {
  return [{
    json: {
      ...entrada,
      status: "skipped",
      razon,
      ...extra
    }
  }];
}

const sourceUrl = String(entrada.source_url || "");
const host = obtenerHost(sourceUrl);
const path = obtenerPath(sourceUrl);
const lang = obtenerLang(sourceUrl);
const idiomaDeclarado = String(entrada.language || "").toLowerCase();
const idiomasNoEspanoles = new Set(["de", "deu", "en", "eng", "fr", "fra", "it", "ita", "por", "pt"]);
const hostsPermitidos = new Set(["churchofjesuschrist.org", "discursosud.com", "speeches.byu.edu"]);

if (!sourceUrl || !host) {
  return omitido("La URL de origen no es valida.");
}

if (!hostsPermitidos.has(host)) {
  return omitido("La fuente no esta autorizada para esta ingesta.");
}

if (idiomasNoEspanoles.has(idiomaDeclarado)) {
  return omitido("El idioma declarado no es espanol.");
}

if (idiomasNoEspanoles.has(lang)) {
  return omitido("La URL declara un idioma no espanol.");
}

if (host === "churchofjesuschrist.org" && lang !== "spa") {
  return omitido("La pagina oficial no declara lang=spa.");
}

if (host === "speeches.byu.edu" && !path.startsWith("/spa/")) {
  return omitido("BYU Speeches solo admite discursos bajo /spa/.");
}

const headers = respuesta.headers || {};
const contentType = String(headers["content-type"] || headers["Content-Type"] || respuesta.contentType || "").toLowerCase();
const httpStatus = Number(respuesta.statusCode || respuesta.status || 0);
const body =
  typeof respuesta.body === "string"
    ? respuesta.body
    : typeof respuesta.data === "string"
      ? respuesta.data
      : typeof respuesta === "string"
        ? respuesta
        : "";

if (httpStatus !== 200) {
  return omitido("La fuente no respondio HTTP 200.", {
    tipo_recurso: "desconocido",
    http_status: httpStatus || null
  });
}

const parecePdf = contentType.includes("application/pdf") || /\.pdf(?:$|[?#])/i.test(sourceUrl) || body.startsWith("%PDF-");
const pareceHtml = contentType.includes("text/html") || /<(?:html|body|main|article|h1|p)\b/i.test(body);
const pareceTexto = contentType.includes("text/plain") && body.trim().length > 0;

if (parecePdf) {
  return omitido("skipped_pdf_pending: la extraccion de PDF no esta habilitada en este workflow.", {
    tipo_recurso: "pdf",
    content_type: "application/pdf",
    http_status: httpStatus
  });
}

if (!pareceHtml && !pareceTexto) {
  return omitido("El recurso no parece HTML ni texto limpio.", {
    tipo_recurso: "desconocido",
    http_status: httpStatus
  });
}

return [{
  json: {
    ...entrada,
    status: "recurso_detectado",
    tipo_recurso: pareceTexto ? "text" : "html",
    content_type: pareceTexto ? "text/plain" : "text/html",
    raw_content: body,
    http_status: httpStatus
  }
}];

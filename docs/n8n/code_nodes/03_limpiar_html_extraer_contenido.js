function decodeEntities(value) {
  const named = {
    amp: "&",
    apos: "'",
    gt: ">",
    ldquo: "\"",
    lsquo: "'",
    lt: "<",
    nbsp: " ",
    ndash: "-",
    mdash: "-",
    quot: "\"",
    rdquo: "\"",
    rsquo: "'"
  };
  return String(value || "")
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&([a-z]+);/gi, (match, name) => named[name.toLowerCase()] || match);
}

function normalizarTexto(value, conservarSaltos = false) {
  let texto = decodeEntities(value)
    .replace(/\u00a0/g, " ")
    .replace(/\u200b/g, "")
    .replace(/Ã‚/g, "")
    .replace(/ÃƒÂ±/g, "n")
    .replace(/Ã±/g, "n")
    .replace(/Ã¡/g, "a")
    .replace(/Ã©/g, "e")
    .replace(/Ã­/g, "i")
    .replace(/Ã³/g, "o")
    .replace(/Ãº/g, "u")
    .replace(/Ã¼/g, "u")
    .replace(/Ã¢â‚¬Å“|Ã¢â‚¬Â|â€œ|â€/g, "\"")
    .replace(/Ã¢â‚¬â„¢|â€™/g, "'")
    .normalize("NFC");
  if (conservarSaltos) {
    return texto
      .split(/\r?\n/)
      .map((linea) => linea.replace(/[^\S\n]+/g, " ").trim())
      .filter(Boolean)
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  return texto.replace(/\s+/g, " ").trim();
}

function firstMatch(html, patterns) {
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match && match[1]) return normalizarTexto(match[1].replace(/<[^>]+>/g, " "));
  }
  return null;
}

function absoluteCanonical(href, fallback) {
  const value = decodeEntities(href).trim();
  if (/^https:\/\//i.test(value)) return value;
  if (value.startsWith("/")) {
    const host = String(fallback || "").match(/^(https:\/\/[^\/?#]+)/i);
    return host ? host[1] + value : fallback;
  }
  return fallback;
}

function canonicalFrom(html, fallback) {
  const links = html.match(/<link\b[^>]*>/gi) || [];
  for (const link of links) {
    if (!/\brel\s*=\s*["'][^"']*canonical/i.test(link)) continue;
    const href = link.match(/\bhref\s*=\s*["']([^"']+)["']/i);
    if (href && href[1]) return absoluteCanonical(href[1], fallback);
  }
  return fallback;
}

function authorFrom(html) {
  const metaTags = html.match(/<meta\b[^>]*>/gi) || [];
  for (const tag of metaTags) {
    if (!/\b(?:name|property)\s*=\s*["'](?:author|article:author|citation_author)["']/i.test(tag)) continue;
    const content = tag.match(/\bcontent\s*=\s*["']([^"']+)["']/i);
    if (content && content[1]) {
      const candidate = decodeEntities(content[1]).replace(/^por\s+/i, "").trim();
      if (!/(anonimo|desconocido|comentario)/i.test(candidate)) return candidate;
    }
  }
  const candidate = firstMatch(html, [
    /<(?:strong|b)[^>]*>\s*(?:por el|por la|por)\s+([^<]{3,120})<\/(?:strong|b)>/i,
    /<(?:p|div|span)[^>]+class=["'][^"']*(?:byline|speaker)[^"']*["'][^>]*>([\s\S]*?)<\/(?:p|div|span)>/i
  ]);
  return candidate && !/(anonimo|desconocido|comentario)/i.test(candidate)
    ? candidate.replace(/^(?:por\s+)?(?:el|la)\s+/i, "").trim()
    : null;
}

const item = $json;
if (item.status === "skipped") {
  return [{ json: item }];
}

const raw = String(item.raw_content || "");
const title = firstMatch(raw, [
  /<h1\b[^>]*>([\s\S]*?)<\/h1>/i,
  /<title\b[^>]*>([\s\S]*?)<\/title>/i
]);
const author = authorFrom(raw);
const canonicalUrl = item.tipo_recurso === "html" ? canonicalFrom(raw, item.source_url) : item.source_url;

let contenido = "";
if (item.tipo_recurso === "text") {
  contenido = normalizarTexto(raw, true);
} else {
  const html = raw
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<(script|style|nav|footer|header|aside|noscript|form|svg|button|iframe)\b[^>]*>[\s\S]*?<\/\1>/gi, " ");
  const principal =
    (html.match(/<article\b[^>]*>([\s\S]*?)<\/article>/i) || [])[1] ||
    (html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i) || [])[1] ||
    (html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i) || [])[1] ||
    html;
  const lineas = decodeEntities(
    principal
      .replace(/<(br|\/p|\/li|\/h[1-6]|\/blockquote|\/section|\/div)>/gi, "\n")
      .replace(/<[^>]+>/g, " ")
  )
    .split(/\n+/)
    .map((linea) => normalizarTexto(linea))
    .filter((linea) => linea.length >= 20);
  const vistas = new Set();
  const basura = /^(inicio|menu|buscar|compartir|descargar|siguiente|anterior|todos los derechos|privacy|cookies?)\b/i;
  contenido = lineas
    .filter((linea) => {
      const key = linea.toLowerCase();
      if (basura.test(linea) || vistas.has(key)) return false;
      vistas.add(key);
      return true;
    })
    .join("\n\n")
    .trim();
}

return [{
  json: {
    ...item,
    status: "contenido_extraido",
    title: normalizarTexto(title || item.title || ""),
    author: normalizarTexto(author || item.author || "") || null,
    source_name: normalizarTexto(item.source_name || ""),
    canonical_url: canonicalUrl,
    content: normalizarTexto(contenido, true),
    extracted_at: new Date().toISOString(),
    extractor_version: "n8n-html-regex-v2",
    raw_content: undefined
  }
}];

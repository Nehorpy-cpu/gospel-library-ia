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
  return value
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&([a-z]+);/gi, (match, name) => named[name.toLowerCase()] ?? match);
}

function normalizarTextoEspanol(value, conservarSaltos = false) {
  let texto = decodeEntities(String(value ?? ""));
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
  if (conservarSaltos) {
    return texto
      .split(/\r?\n/)
      .map((linea) => linea.replace(/[^\S\n]+/g, " ").trim())
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  return texto.replace(/\s+/g, " ").trim();
}

function firstMatch(html, patterns) {
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match?.[1]) return normalizarTextoEspanol(match[1].replace(/<[^>]+>/g, " "));
  }
  return null;
}

function canonicalFrom(html, fallback) {
  const links = html.match(/<link\b[^>]*>/gi) ?? [];
  for (const link of links) {
    if (!/\brel\s*=\s*["'][^"']*canonical/i.test(link)) continue;
    const href = link.match(/\bhref\s*=\s*["']([^"']+)["']/i)?.[1];
    if (href) {
      try {
        return new URL(decodeEntities(href), fallback).toString();
      } catch {
        return fallback;
      }
    }
  }
  return fallback;
}

function authorFrom(html) {
  const metaTags = html.match(/<meta\b[^>]*>/gi) ?? [];
  for (const tag of metaTags) {
    if (!/\b(?:name|property)\s*=\s*["'](?:author|article:author|citation_author)["']/i.test(tag)) continue;
    const content = tag.match(/\bcontent\s*=\s*["']([^"']+)["']/i)?.[1];
    if (content) {
      const candidate = decodeEntities(content)
        .replace(/^por\s+/i, "")
        .replace(/^(?:el|la)\s+/i, "")
        .trim();
      if (!/(?:anónimo|desconocido|dice:|comentario)/i.test(candidate)) return candidate;
    }
  }
  const candidate = firstMatch(html, [
    /<(?:strong|b)[^>]*>\s*(?:por el|por la|por)\s+([^<]{3,120})<\/(?:strong|b)>/i,
    /<(?:p|div|span)[^>]+class=["'][^"']*(?:byline|speaker)[^"']*["'][^>]*>([\s\S]*?)<\/(?:p|div|span)>/i
  ]);
  return candidate && !/(?:anónimo|desconocido|dice:|comentario)/i.test(candidate)
    ? candidate.replace(/^(?:por\s+)?(?:el|la)\s+/i, "").trim()
    : null;
}

const item = $json;
if (item.status === "skipped") {
  return [{ json: item }];
}

const htmlOriginal = String(item.raw_html ?? "");
const title = firstMatch(htmlOriginal, [
  /<h1\b[^>]*>([\s\S]*?)<\/h1>/i,
  /<title\b[^>]*>([\s\S]*?)<\/title>/i
]);
const canonicalUrl = canonicalFrom(htmlOriginal, item.source_url);
const author = authorFrom(htmlOriginal);

let html = htmlOriginal
  .replace(/<!--[\s\S]*?-->/g, " ")
  .replace(/<(script|style|nav|footer|header|aside|noscript|form|svg|button)\b[^>]*>[\s\S]*?<\/\1>/gi, " ");

const principal =
  html.match(/<article\b[^>]*>([\s\S]*?)<\/article>/i)?.[1] ??
  html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)?.[1] ??
  html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i)?.[1] ??
  html;

const lineas = decodeEntities(
  principal
    .replace(/<(br|\/p|\/li|\/h[1-6]|\/blockquote|\/section|\/div)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
)
  .split(/\n+/)
  .map((linea) => linea.replace(/\s+/g, " ").trim())
  .filter((linea) => linea.length >= 20);

const vistas = new Set();
const basura = /^(inicio|menú|buscar|compartir|descargar|siguiente|anterior|todos los derechos|privacy|cookies?)\b/i;
const contenido = lineas
  .filter((linea) => {
    const key = linea.toLowerCase();
    if (basura.test(linea) || vistas.has(key)) return false;
    vistas.add(key);
    return true;
  })
  .join("\n\n")
  .trim();

return [{
  json: {
    ...item,
    status: "contenido_extraido",
    title: normalizarTextoEspanol(title ?? item.title ?? ""),
    author: normalizarTextoEspanol(author ?? item.author ?? "") || null,
    source_name: normalizarTextoEspanol(item.source_name ?? ""),
    canonical_url: canonicalUrl,
    content: normalizarTextoEspanol(contenido, true),
    extracted_at: new Date().toISOString(),
    extractor_version: "n8n-html-regex-v1",
    raw_html: undefined
  }
}];

const item = $json;
if (item.status === "skipped") {
  return [{ json: item }];
}

function obtenerLang(url) {
  const match = String(url || "").match(/[?&]lang=([^&#]+)/i);
  return match ? decodeURIComponent(match[1]).toLowerCase() : "";
}

function skipped(razon) {
  return [{
    json: {
      ...item,
      status: "skipped",
      razon,
      content: undefined
    }
  }];
}

const texto = String(item.content || "").trim();
const titulo = String(item.title || "").trim();
const idioma = String(item.language || "es").trim().toLowerCase();
const sourceUrl = String(item.source_url || "");
const canonicalUrl = String(item.canonical_url || "");
const idiomasNoEspanoles = new Set(["de", "deu", "en", "eng", "fr", "fra", "it", "ita", "por", "pt"]);
const frasesProhibidas = [
  "[reemplazar antes de enviar]",
  "documento de prueba",
  "no es una cita oficial",
  "no reemplaza ninguna fuente doctrinal",
  "contenido de prueba",
  "placeholder"
];
const textoAuditable = (titulo + "\n" + texto + "\n" + String(item.summary || "")).toLowerCase();
const palabras = (texto.toLowerCase().match(/[a-záéíóúüñ]+/g) || []);
const marcadoresEs = new Set([
  "al", "como", "con", "cristo", "de", "del", "dios", "el", "en", "es",
  "evangelio", "jesucristo", "la", "las", "los", "para", "por", "que",
  "se", "su", "una", "y"
]);
const marcadoresEn = new Set([
  "and", "are", "christ", "for", "from", "god", "is", "jesus", "of", "that",
  "the", "this", "to", "was", "with", "you"
]);
const cuentaEs = palabras.filter((palabra) => marcadoresEs.has(palabra)).length;
const cuentaEn = palabras.filter((palabra) => marcadoresEn.has(palabra)).length;
const proporcionEs = palabras.length ? cuentaEs / palabras.length : 0;
const basuraNavegacion = (texto.match(/\b(inicio|menu|buscar|compartir|suscribete|cookies?|privacidad|siguiente|anterior)\b/gi) || []).length;

if (!/^https:\/\//i.test(sourceUrl)) {
  return skipped("La URL de origen no es valida.");
}

if (sourceUrl.toLowerCase().includes("prueba-n8n")) {
  return skipped("La URL corresponde a una prueba n8n.");
}

if (idioma && idioma !== "es" && idioma !== "spa") {
  return skipped("El idioma declarado no es espanol.");
}

if (idiomasNoEspanoles.has(obtenerLang(sourceUrl)) || idiomasNoEspanoles.has(obtenerLang(canonicalUrl))) {
  return skipped("La URL declara un idioma no espanol.");
}

if (frasesProhibidas.some((frase) => textoAuditable.includes(frase))) {
  return skipped("El documento contiene texto de prueba o placeholder.");
}

if (!titulo || titulo.length < 3) {
  return skipped("No se pudo extraer un titulo confiable.");
}

if (texto.length < 300) {
  return skipped("El texto limpio tiene menos de 300 caracteres.");
}

if (palabras.length < 60) {
  return skipped("El documento contiene muy pocas palabras utiles.");
}

if (cuentaEs < 8 || proporcionEs < 0.025 || cuentaEn > cuentaEs) {
  return skipped("La heuristica no pudo confirmar que el contenido este en espanol.");
}

if (basuraNavegacion > 12) {
  return skipped("El contenido parece contener navegacion o texto repetido.");
}

return [{
  json: {
    ...item,
    status: "ready",
    language: "es",
    content: texto,
    validacion: {
      caracteres: texto.length,
      palabras: palabras.length,
      marcadores_es: cuentaEs,
      marcadores_en: cuentaEn
    }
  }
}];

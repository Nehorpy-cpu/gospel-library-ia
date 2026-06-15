const item = $json;
if (item.status === "skipped") {
  return [{ json: item }];
}

const texto = String(item.content ?? "").trim();
const titulo = String(item.title ?? "").trim();
const idioma = String(item.language ?? "").trim().toLowerCase();
const urls = [item.source_url, item.canonical_url].filter(Boolean).map((url) => String(url));
const idiomasNoEspanoles = new Set(["de", "deu", "en", "eng", "fr", "fra", "it", "ita", "por", "pt"]);
const frasesProhibidas = [
  "[reemplazar antes de enviar]",
  "documento de prueba",
  "no es una cita oficial",
  "no reemplaza ninguna fuente doctrinal",
  "contenido de prueba",
  "placeholder"
];
const textoAuditable = `${titulo}\n${texto}\n${String(item.summary ?? "")}`.toLowerCase();
const palabras = (texto.toLowerCase().match(/[a-záéíóúüñ]+/g) ?? []);
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
const basuraNavegacion = (
  texto.match(/\b(inicio|menú|buscar|compartir|suscríbete|cookies?|privacidad|siguiente|anterior)\b/gi) ?? []
).length;

let razon = null;
if (idiomasNoEspanoles.has(idioma)) {
  razon = `El idioma declarado '${idioma}' no es español.`;
} else if (urls.some((url) => {
  try {
    return idiomasNoEspanoles.has(String(new URL(url).searchParams.get("lang") ?? "").toLowerCase());
  } catch {
    return true;
  }
})) {
  razon = "La URL declara un idioma no español o no es válida.";
} else if (frasesProhibidas.some((frase) => textoAuditable.includes(frase))) {
  razon = "El documento contiene texto de prueba o placeholder.";
} else if (!titulo || titulo.length < 3) {
  razon = "No se pudo extraer un título confiable.";
} else if (texto.length < 301) {
  razon = "El texto limpio tiene menos de 301 caracteres.";
} else if (palabras.length < 60) {
  razon = "El documento contiene muy pocas palabras útiles.";
} else if (cuentaEs < 8 || proporcionEs < 0.025 || cuentaEn > cuentaEs) {
  razon = "La heurística no pudo confirmar que el contenido esté en español.";
} else if (basuraNavegacion > 12) {
  razon = "El contenido parece contener navegación o texto repetido.";
}

if (razon) {
  return [{
    json: {
      ...item,
      status: "skipped",
      razon,
      content: undefined
    }
  }];
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

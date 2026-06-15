const item = $json;
if (item.status === "skipped") {
  return [{ json: item }];
}

const texto = String(item.content ?? "").trim();
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
if (!item.title || String(item.title).trim().length < 3) {
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

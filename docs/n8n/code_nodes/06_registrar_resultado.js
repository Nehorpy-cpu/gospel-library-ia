const actual = $json;
const preparado = actual.status === "skipped"
  ? actual
  : $("Preparar payload para Gospel Library IA").item.json;
const respuesta = actual;

function parseBody(value) {
  if (value && typeof value.body === "object") return value.body;
  if (value && typeof value.body === "string") {
    try {
      return JSON.parse(value.body);
    } catch {
      return {};
    }
  }
  return value && typeof value === "object" ? value : {};
}

function detalleEnEspanol(value) {
  if (!value) return null;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => item && (item.msg || item.message) ? item.msg || item.message : JSON.stringify(item))
      .filter(Boolean)
      .join("; ");
  }
  return value.msg || value.message || JSON.stringify(value);
}

function registrarResultado(resultado) {
  const data = $getWorkflowStaticData("global");
  if (!Array.isArray(data.gospel_library_ingestion_results)) {
    data.gospel_library_ingestion_results = [];
  }
  data.gospel_library_ingestion_results.push(resultado);
  return [{ json: resultado }];
}

const body = parseBody(respuesta);
const httpStatus = Number(respuesta.statusCode || respuesta.status || 200);
const title = preparado.title || null;
const sourceUrl = preparado.source_url || null;
const sourceName = preparado.source_name || null;
const language = preparado.language || null;

if (preparado.status === "skipped") {
  return registrarResultado({
    resultado: "skipped",
    title,
    source_url: sourceUrl,
    source_name: sourceName,
    language,
    chunks_count: null,
    document_id: null,
    mensaje: preparado.razon || "Documento omitido por validacion.",
    http_status: null
  });
}

if (body && ["created", "verified_existing", "skipped", "rejected"].includes(body.status)) {
  const chunksCount = Number(body.chunks_count || body.chunks || 0);
  const mensajes = {
    created: "Documento creado correctamente.",
    verified_existing: "El documento ya existia y fue verificado.",
    skipped: "La API omitio el documento.",
    rejected: "La API rechazo el documento."
  };
  return registrarResultado({
    resultado: body.status,
    title,
    source_url: sourceUrl,
    source_name: sourceName,
    language,
    chunks_count: Number.isFinite(chunksCount) ? chunksCount : null,
    document_id: body.document_id || (body.document && body.document.id) || null,
    mensaje: mensajes[body.status] || "Resultado registrado.",
    http_status: httpStatus
  });
}

const mensajeApi = detalleEnEspanol(body.detail || body.error || body.message);

return registrarResultado({
  resultado: httpStatus >= 400 ? "error" : "rejected",
  title,
  source_url: sourceUrl,
  source_name: sourceName,
  language,
  chunks_count: null,
  document_id: null,
  mensaje: mensajeApi || ("La API respondio HTTP " + httpStatus + "."),
  http_status: httpStatus
});

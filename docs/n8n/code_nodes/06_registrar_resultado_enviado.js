const preparado = $("Preparar payload para Gospel Library IA").item.json;
const respuesta = $json;

function parseBody(value) {
  if (value && typeof value.body === "object" && value.body !== null) return value.body;
  if (value && typeof value.body === "string") {
    try {
      return JSON.parse(value.body);
    } catch {
      return {};
    }
  }
  if (value && typeof value.data === "object" && value.data !== null) return value.data;
  if (value && typeof value.data === "string") {
    try {
      return JSON.parse(value.data);
    } catch {
      return {};
    }
  }
  return value && typeof value === "object" ? value : {};
}

function previewSeguro(value) {
  const texto = JSON.stringify(value || {});
  return texto.length > 500 ? texto.slice(0, 500) + "..." : texto;
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
const apiStatus = String(body.status || "").trim();
const chunksCount = Number(body.chunks_count || body.chunks || 0);
const base = {
  title: preparado.title || null,
  source_url: preparado.source_url || null,
  source_name: preparado.source_name || null,
  language: preparado.language || null,
  chunks_count: Number.isFinite(chunksCount) ? chunksCount : null,
  document_id: body.document_id || body.id || (body.document && body.document.id) || null,
  http_status: httpStatus
};

if (httpStatus >= 400) {
  return registrarResultado({
    resultado: "error",
    ...base,
    chunks_count: null,
    document_id: null,
    mensaje: "La API respondio HTTP " + httpStatus + ".",
    api_body_preview: previewSeguro(body)
  });
}

if (apiStatus === "created") {
  return registrarResultado({
    resultado: "created",
    ...base,
    mensaje: "Documento creado correctamente."
  });
}

if (apiStatus === "verified_existing") {
  return registrarResultado({
    resultado: "verified_existing",
    ...base,
    mensaje: "El documento ya existia y fue verificado."
  });
}

if (apiStatus === "skipped") {
  return registrarResultado({
    resultado: "skipped",
    ...base,
    mensaje: body.message || body.detail || "La API omitio el documento."
  });
}

if (apiStatus === "rejected") {
  return registrarResultado({
    resultado: "rejected",
    ...base,
    mensaje: body.message || body.detail || "La API rechazo el documento."
  });
}

return registrarResultado({
  resultado: "error",
  ...base,
  chunks_count: null,
  document_id: null,
  mensaje: "La API respondio HTTP " + httpStatus + " pero no devolvio un status reconocible.",
  api_body_preview: previewSeguro(body)
});

const preparado = $("Preparar payload para Gospel Library IA").item.json;
const respuesta = $json;
const body =
  respuesta && typeof respuesta.body === "object"
    ? respuesta.body
    : respuesta && typeof respuesta.body === "string"
      ? (() => {
          try { return JSON.parse(respuesta.body); } catch { return {}; }
        })()
      : respuesta;
const httpStatus = Number(respuesta.statusCode ?? respuesta.status ?? 200);

if (preparado.status === "skipped") {
  return [{
    json: {
      resultado: "skipped",
      source_url: preparado.source_url,
      title: preparado.title ?? null,
      mensaje: preparado.razon ?? "Documento omitido por validación."
    }
  }];
}

if (body?.status === "created" || body?.status === "verified_existing") {
  return [{
    json: {
      resultado: body.status,
      source_url: preparado.source_url,
      title: preparado.title,
      document_id: body.document_id,
      chunks: body.chunks,
      mensaje: body.status === "created"
        ? "Documento creado correctamente."
        : "El documento ya existía y fue verificado."
    }
  }];
}

return [{
  json: {
    resultado: httpStatus >= 500 ? "error" : "rejected",
    source_url: preparado.source_url,
    title: preparado.title ?? null,
    mensaje: body?.detail
      ? JSON.stringify(body.detail)
      : `La API respondió HTTP ${httpStatus}.`
  }
}];

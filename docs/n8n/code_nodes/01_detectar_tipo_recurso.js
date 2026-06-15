const entrada = $("Procesar una URL por vez").item.json;
const respuesta = $json;
const headers = respuesta.headers ?? {};
const contentType = String(
  headers["content-type"] ??
  headers["Content-Type"] ??
  respuesta.contentType ??
  ""
).toLowerCase();
const httpStatus = Number(respuesta.statusCode ?? respuesta.status ?? 200);
const body =
  typeof respuesta.body === "string"
    ? respuesta.body
    : typeof respuesta.data === "string"
      ? respuesta.data
      : typeof respuesta === "string"
        ? respuesta
        : "";
const sourceUrl = String(entrada.source_url ?? "");
const parecePdf =
  contentType.includes("application/pdf") ||
  /\.pdf(?:$|[?#])/i.test(sourceUrl) ||
  body.startsWith("%PDF-");
const pareceHtml =
  contentType.includes("text/html") ||
  /<(?:html|body|main|article|h1|p)\b/i.test(body);

if (httpStatus >= 400) {
  return [{
    json: {
      ...entrada,
      status: "skipped",
      tipo_recurso: "desconocido",
      razon: `La fuente respondió HTTP ${httpStatus}.`,
      http_status: httpStatus
    }
  }];
}

if (parecePdf) {
  return [{
    json: {
      ...entrada,
      status: "skipped",
      tipo_recurso: "pdf",
      content_type: "application/pdf",
      razon: "skipped_pdf_pending: la extracción de PDF no está habilitada en este workflow.",
      http_status: httpStatus
    }
  }];
}

if (!pareceHtml) {
  return [{
    json: {
      ...entrada,
      status: "skipped",
      tipo_recurso: "desconocido",
      razon: "El recurso no parece HTML ni PDF.",
      http_status: httpStatus
    }
  }];
}

return [{
  json: {
    ...entrada,
    status: "html_detectado",
    tipo_recurso: "html",
    content_type: "text/html",
    raw_html: body,
    http_status: httpStatus
  }
}];

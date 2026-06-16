const data = $getWorkflowStaticData("global");
const resultados = Array.isArray(data.gospel_library_ingestion_results)
  ? data.gospel_library_ingestion_results
  : [];

const contador = {
  total_procesados: resultados.length,
  creados: 0,
  existentes: 0,
  omitidos: 0,
  rechazados: 0,
  errores: 0
};

const titulosCreados = [];
const urlsRechazadas = [];

for (const item of resultados) {
  if (item.resultado === "created") {
    contador.creados += 1;
    if (item.title) titulosCreados.push(item.title);
  } else if (item.resultado === "verified_existing") {
    contador.existentes += 1;
  } else if (item.resultado === "skipped") {
    contador.omitidos += 1;
  } else if (item.resultado === "rejected") {
    contador.rechazados += 1;
    urlsRechazadas.push({
      source_url: item.source_url || null,
      title: item.title || null,
      razon: item.mensaje || "Documento rechazado."
    });
  } else if (item.resultado === "error") {
    contador.errores += 1;
    urlsRechazadas.push({
      source_url: item.source_url || null,
      title: item.title || null,
      razon: item.mensaje || "Error durante la ingesta."
    });
  }
}

const mensaje = [
  "Procesados: " + contador.total_procesados,
  "creados: " + contador.creados,
  "existentes: " + contador.existentes,
  "omitidos: " + contador.omitidos,
  "rechazados: " + contador.rechazados,
  "errores: " + contador.errores
].join("; ");

return [{
  json: {
    resultado: "batch_summary",
    mensaje,
    started_at: data.gospel_library_ingestion_started_at || null,
    finished_at: new Date().toISOString(),
    ...contador,
    titulos_creados: titulosCreados,
    urls_rechazadas: urlsRechazadas,
    resultados
  }
}];

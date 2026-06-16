const item = $json;

function registrarResultado(resultado) {
  const data = $getWorkflowStaticData("global");
  if (!Array.isArray(data.gospel_library_ingestion_results)) {
    data.gospel_library_ingestion_results = [];
  }
  data.gospel_library_ingestion_results.push(resultado);
  return [{ json: resultado }];
}

return registrarResultado({
  resultado: "skipped",
  title: item.title || null,
  source_url: item.source_url || null,
  source_name: item.source_name || null,
  language: item.language || null,
  chunks_count: null,
  document_id: null,
  mensaje: item.razon || "Documento omitido por validacion.",
  http_status: null
});

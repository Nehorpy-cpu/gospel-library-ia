const data = $getWorkflowStaticData("global");
data.gospel_library_ingestion_results = [];
data.gospel_library_ingestion_started_at = new Date().toISOString();

return $input.all();

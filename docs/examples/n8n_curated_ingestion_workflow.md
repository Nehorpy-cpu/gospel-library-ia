# Flujo de ingesta curada en español con n8n

Este flujo es manual o de baja frecuencia. No recorre enlaces y procesa una
URL explícita por elemento.

## Nodos

1. **Inicio manual o programado**
   - Comienza manualmente durante la validación.
   - Si se programa después, usa baja frecuencia y una lista fija pequeña.

2. **URLs curadas**
   - Cada elemento contiene `source_url`, `source_name`, `content_type` y tags.
   - Fuentes permitidas:
     - documentos individuales de `https://discursosud.com/`;
     - discursos bajo `https://speeches.byu.edu/spa/talks/`;
     - recursos `/study/...` con `lang=spa` del sitio oficial.
   - No uses portadas, buscadores, categorías ni listados.
   - No descubras enlaces desde las páginas descargadas.

3. **Descargar recurso**
   - Método `GET`.
   - Timeout de 30 segundos.
   - Respuesta como texto.
   - User-Agent identificable y `Accept-Language` en español.
   - Lote de una URL y pausa entre solicitudes.

4. **Detectar recurso**
   - Clasifica HTML, PDF o contenido desconocido.
   - Los PDF quedan `skipped_pdf_pending`.
   - No envía binarios a Gospel Library IA.

5. **Limpiar HTML**
   - Extrae título, autor y canonical.
   - Prioriza `article`, luego `main`.
   - Elimina scripts, estilos, navegación, encabezado, pie y elementos
     repetidos.
   - Devuelve únicamente texto normalizado.

6. **Validar español**
   - Exige más de 300 caracteres.
   - Comprueba marcadores frecuentes del español.
   - Rechaza contenido predominantemente inglés o navegación.

7. **Preparar payload**
   - Construye el contrato documentado en
     `docs/examples/n8n_ingestion_payload_es.json`.
   - No incluye secretos, HTML, `file_url`, `storage_path` ni archivos.

8. **Enviar a la API**
   - `POST https://api.estudiopy.com/api/ingestion/documents`
   - Header `X-Ingestion-Key` desde variable o credencial.
   - Registra `created`, `verified_existing`, `skipped`, `rejected` o `error`.

## Lotes recomendados

- Comienza con una a tres URLs.
- No superes cinco URLs durante pruebas.
- Usa batch size 1.
- Espera tres segundos entre fuentes.
- No reintentes páginas externas más de dos veces.
- La llamada a la API puede repetirse porque es idempotente.

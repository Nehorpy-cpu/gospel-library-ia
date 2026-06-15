# n8n Curated Spanish Ingestion Workflow

This workflow is intentionally manual or low-frequency. It does not crawl links
and processes one explicit Spanish URL per item.

## Nodes

1. **Manual Trigger** or **Schedule Trigger**
   - Start manually during validation.
   - If scheduled later, use a low frequency and a small fixed URL list.

2. **Code: Curated URLs**
   - Return items with `source_url`, `source_name`, `content_type`, and default
     tags.
   - Use explicit URLs ending in `?lang=spa` when the source supports it.
   - Allowed sources:
     - individual resources from `https://discursosud.com/`;
     - individual Spanish talks under `https://speeches.byu.edu/spa/talks/`;
     - `/study/...` resources with `lang=spa` from
       `https://www.churchofjesuschrist.org/`.
   - Do not enqueue home pages, search pages, category archives, or the BYU
     `/spa/talks/` listing.
   - Do not discover or enqueue links from downloaded pages.

3. **HTTP Request: Download Source**
   - Method: `GET`
   - URL: `{{$json.source_url}}`
   - Timeout: 30 seconds
   - Response: text
   - Send a respectful User-Agent identifying the workflow and
     `https://www.estudiopy.com`.
   - Process one item at a time and wait between external requests.

4. **HTML Extract**
   - Extract the page `h1`, author/byline, publication date, canonical link,
     and the known main article container.
   - Remove `script`, `style`, `nav`, `header`, `footer`, `aside`, forms,
     cookie notices, related content, and duplicated blocks.
   - For an approved PDF URL, use a bounded PDF text extraction node or
     service, retain the original PDF URL, and do not send the binary file to
     Gospel Library IA.

5. **Code: Validate Spanish and Clean Text**
   - Convert extracted blocks to plain text.
   - Preserve paragraph breaks.
   - Reject content under 301 characters.
   - Reject output containing raw structural HTML.
   - Confirm `es`/`spa`; send failures to a review branch.

6. **Set: Prepare API Payload**
   - Build the fields documented in
     `docs/examples/n8n_ingestion_payload_es.json`.
   - Do not include credentials, downloaded files, HTML, `file_url`, or
     `storage_path`.
   - Set `content_type` to `application/pdf` only when `content` contains clean
     text already extracted from the PDF.

7. **HTTP Request: Gospel Library IA**
   - Method: `POST`
   - URL: `https://api.estudiopy.com/api/ingestion/documents`
   - Header: `X-Ingestion-Key` from an n8n credential or secret variable.
   - Header: `Content-Type: application/json`
   - Body: JSON from the previous node.

8. **Switch: Record Result**
   - `created`: record the returned document ID.
   - `verified_existing`: record that the item was already present.
   - `401`: verify the n8n credential and Render variable without logging it.
   - `422`: send the validation detail and URL to manual review.
   - `5xx`: retry with bounded exponential backoff; do not create a scraping
     loop.

## Suggested batching

- Start with 1-5 explicit URLs.
- Use batch size 1.
- Wait at least one second between external source requests.
- Do not automatically retry source pages more than twice.
- The API call may be retried safely because document ingestion is idempotent.

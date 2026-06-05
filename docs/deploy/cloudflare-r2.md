# Cloudflare R2

## Usage

R2 stores downloaded PDFs, audio, video references, OCR artifacts, and extracted
source files produced by the scraper workers.

## Variables

```txt
R2_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=gospel-library-assets
R2_REGION=auto
```

The production examples also include `STORAGE_*` aliases for provider-neutral
documentation. Current code reads the `R2_*` names.

## Object naming

Use deterministic keys:

```txt
sources/{source_key}/{document_id}/original.{ext}
sources/{source_key}/{document_id}/ocr.txt
sources/{source_key}/{document_id}/transcript.txt
```

Keep source assets private by default. Serve public files through signed URLs or
application-controlled routes when user access rules are added.

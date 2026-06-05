# Scraping Ethics

Gospel Library IA must be conservative with doctrinal sources.

## Rules

- Respect `robots.txt`.
- Keep `CRAWLER_RESPECT_ROBOTS_TXT=true`.
- Use low concurrency and delays for public sites.
- Run small source-specific crawls before wider ingestion.
- Do not bypass access controls, paywalls, authentication, or anti-bot walls.
- Do not scrape private user data.
- Do not retry aggressively after blocks or rate limits.
- Do not download large media collections without explicit approval.
- Prefer official APIs or bulk/public data exports when available.

## Source Sensitivity

Official Church sources should be treated with extra care:

- General Conference
- Church manuals
- Come, Follow Me
- Teachings of Presidents
- Scriptures

Joseph Smith Papers is historical/documentary source material. The app should label it as historical context, not as a current official doctrinal manual.

## Operational Defaults

The default source catalog uses small `maxPagesPerRun` values:

- 8 to 12 pages per source run.
- source-level admin controls for pausing and limiting crawls.
- incremental URL deduplication before worker fetch.
- content hash checks before updating documents.

Increase limits only after reviewing robots policy, server behavior, and operator intent.

# Sentry Setup

## Projects

Create separate Sentry projects:

- `gospel-library-web`
- `gospel-library-rag`
- `gospel-library-scraper`

## Environment Variables

```txt
SENTRY_DSN
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=<git-sha>
NEXT_PUBLIC_SENTRY_DSN
```

## Recommended Alerts

- error rate above 2 percent for 10 minutes
- RAG API p95 latency above 8 seconds
- chat stream failures above 5 percent
- worker task failure spike
- scraper anti-block failures above threshold

## Data Hygiene

- Do not send user prompts containing sensitive personal data unless consent and retention policy are clear.
- Scrub authorization headers.
- Scrub cookies and refresh tokens.
- Scrub OpenAI keys and R2 credentials.

# Cloudflare WAF And Edge Policy

## DNS

```txt
gospellibraryia.com        -> Vercel or Kubernetes ingress
api.gospellibraryia.com    -> Kubernetes ingress / Railway API gateway
assets.gospellibraryia.com -> Cloudflare R2 public bucket or signed route
```

## SSL

- Mode: Full strict
- Always Use HTTPS: enabled
- Minimum TLS: 1.2
- HTTP/2 and HTTP/3: enabled
- HSTS: enabled after production validation

## WAF Custom Rules

### Block Known Bad Bots

```txt
if cf.bot_management.score < 10 and not cf.client.bot
then block
```

### Rate Limit RAG Chat

```txt
path starts with /api/rag/chat
threshold: 30 requests / 1 minute / IP
action: managed challenge
```

### Rate Limit Search

```txt
path starts with /api/rag/search or /api/rag
threshold: 120 requests / 1 minute / IP
action: throttle
```

### Protect Admin

```txt
path starts with /admin or /api/scraper
require:
  country allowlist or Zero Trust Access policy
```

### Upload Size

```txt
path starts with /api/uploads
max body size: plan limit
action: block over limit
```

## Cache Rules

### Static Assets

```txt
/_next/static/*
cache: cache everything
edge ttl: 30 days
browser ttl: 30 days
```

### Public Document Thumbnails

```txt
/assets/thumbnails/*
cache: cache everything
edge ttl: 7 days
```

### API

```txt
/api/*
cache: bypass
```

## Security Headers At Edge

```txt
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Use Cloudflare Transform Rules or Nginx/Ingress annotations.

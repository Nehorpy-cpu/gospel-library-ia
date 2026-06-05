const baseUrls = {
  app: process.env.PROD_APP_URL,
  api: process.env.PROD_API_URL,
  rag: process.env.PROD_RAG_URL,
  scraper: process.env.PROD_SCRAPER_URL
};

const checks = [
  ["app", baseUrls.app, "/api/health"],
  ["api", baseUrls.api, "/health"],
  ["api-ready", baseUrls.api, "/ready"],
  ["rag", baseUrls.rag, "/health"],
  ["rag-ready", baseUrls.rag, "/ready"],
  ["scraper", baseUrls.scraper, "/health"],
  ["scraper-ready", baseUrls.scraper, "/ready"]
];

const missing = Object.entries(baseUrls)
  .filter(([, value]) => !value)
  .map(([key]) => `PROD_${key.toUpperCase()}_URL`);

if (missing.length > 0) {
  console.error(`Missing verification URLs: ${missing.join(", ")}`);
  process.exit(1);
}

let failed = false;

for (const [label, base, path] of checks) {
  const url = new URL(path, base).toString();
  try {
    const response = await fetch(url);
    console.log(`${label} ${response.status} ${url}`);
    if (!response.ok) failed = true;
  } catch (error) {
    failed = true;
    console.error(`${label} failed ${url}: ${error.message}`);
  }
}

process.exit(failed ? 1 : 0);

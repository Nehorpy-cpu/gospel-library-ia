const mode = process.argv[2] ?? "check";

const required = [
  "DATABASE_URL",
  "REDIS_URL",
  "QDRANT_URL",
  "QDRANT_API_KEY",
  "QDRANT_COLLECTION",
  "OPENAI_API_KEY"
];

const missing = required.filter((key) => !process.env[key]);

if (missing.length > 0) {
  console.error(`Missing production variables for ${mode}: ${missing.join(", ")}`);
  console.error("Load real secrets in your cloud provider or shell. Do not commit .env.production.");
  process.exit(1);
}

if (mode === "migrate") {
  console.log("Environment looks ready. Run scraper and rag Alembic migrations in the production backend shell:");
  console.log("  cd scraper && alembic upgrade head");
  console.log("  cd rag && alembic upgrade head");
  console.log("Run Prisma migrations only if packages/database is your production migration owner.");
} else if (mode === "seed") {
  console.log("Environment looks ready. Seed production deliberately:");
  console.log("  initialize Qdrant collection doctrinal_chunks_v1");
  console.log("  seed canonical sources");
  console.log("  run a small scraping/indexing batch before massive ingestion");
} else {
  console.log("Production environment variables look ready.");
}

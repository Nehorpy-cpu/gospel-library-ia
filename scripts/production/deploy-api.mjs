console.log("API deploy is provider-managed. Use Railway or Render with these service roots:");
console.log("  apps/api  -> uvicorn app.main:app --host 0.0.0.0 --port $PORT");
console.log("  rag       -> uvicorn app.main:app --host 0.0.0.0 --port $PORT");
console.log("  scraper   -> uvicorn app.api:app --host 0.0.0.0 --port $PORT");
console.log("Workers use the same scraper/rag images with the Celery commands documented in docs/deploy/railway.md.");
console.log("No deploy was triggered automatically.");

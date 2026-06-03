# Gospel Library IA Runbook

## Start Local Full Stack

```bash
cp .env.example .env
docker compose up --build
```

With observability:

```bash
docker compose --profile observability up
```

With Nginx edge:

```bash
docker compose --profile edge up
```

With backups:

```bash
docker compose --profile backup up
```

## Apply Kubernetes

```bash
kubectl apply -k infra/k8s/overlays/production
```

## Rollback Kubernetes

```bash
kubectl rollout undo deployment/web -n gospel-library
kubectl rollout undo deployment/rag-api -n gospel-library
kubectl rollout undo deployment/scraper-api -n gospel-library
```

## Check Health

```bash
curl https://gospellibraryia.example.com
curl https://gospellibraryia.example.com/api/rag/health
curl https://gospellibraryia.example.com/api/scraper/health
```

## Queue Problems

Symptoms:

- chat works but indexing is stale
- embeddings backlog grows
- scraper jobs delayed

Actions:

```bash
kubectl scale deployment rag-worker-indexing --replicas=8 -n gospel-library
kubectl scale deployment scraper-worker-scraping --replicas=8 -n gospel-library
```

Check Redis and worker logs:

```bash
kubectl logs deploy/rag-worker-indexing -n gospel-library
kubectl logs deploy/scraper-worker-scraping -n gospel-library
```

## Qdrant Problems

Actions:

- Check `/healthz`.
- Check disk usage.
- Check collection status.
- Restore latest snapshot if corruption or accidental deletion.

## Database Problems

Actions:

- Check managed provider dashboard.
- Inspect slow queries.
- Pause heavy backfills.
- Scale read replicas.
- Restore PITR only after incident review.

## OpenAI Rate Limit

Actions:

- Reduce worker concurrency.
- Lower embedding batch concurrency.
- Enable retry/backoff.
- Queue indexing overnight.

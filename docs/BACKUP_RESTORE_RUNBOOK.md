# Backup and restore runbook

This runbook covers the local procedures validated during Phase 25. Production
must use managed PostgreSQL PITR, durable Qdrant snapshots, and versioned object
storage in addition to these checks.

## Safety rules

- Never restore over the primary database during a drill.
- Stop scheduler and ingestion workers before taking a consistency snapshot.
- Store dumps and snapshots outside the repository.
- Use a temporary database or collection name containing `restore`.
- Record file size, checksum, source counts, and restored counts.

## PostgreSQL

Stop writers:

```powershell
docker compose stop scraper-scheduler scraper-worker-scraping scraper-worker-assets scraper-worker-ocr scraper-worker-indexing rag-worker-indexing
```

Create a custom-format dump outside Git:

```powershell
$backupDir = Join-Path $env:TEMP "gospel-library-backups"
New-Item -ItemType Directory -Force $backupDir | Out-Null
docker compose exec -T postgres pg_dump -U gospel -d gospel_library -Fc -f /tmp/gospel_library.dump
docker compose cp postgres:/tmp/gospel_library.dump "$backupDir/gospel_library.dump"
Get-FileHash "$backupDir/gospel_library.dump" -Algorithm SHA256
```

Restore into an isolated database:

```powershell
docker compose exec -T postgres dropdb -U gospel --if-exists gospel_library_restore
docker compose exec -T postgres createdb -U gospel gospel_library_restore
Get-Content "$backupDir/gospel_library.dump" -AsByteStream |
  docker compose exec -T postgres pg_restore -U gospel -d gospel_library_restore --no-owner --no-privileges
```

Compare critical row counts before deleting the temporary database:

```powershell
docker compose exec -T postgres psql -U gospel -d gospel_library -c "SELECT count(*) FROM documents;"
docker compose exec -T postgres psql -U gospel -d gospel_library_restore -c "SELECT count(*) FROM documents;"
docker compose exec -T postgres dropdb -U gospel gospel_library_restore
```

## Qdrant

Create and download a snapshot:

```powershell
$snapshot = Invoke-RestMethod -Method Post -Uri "http://localhost:6333/collections/doctrinal_chunks_v1/snapshots"
$snapshotName = $snapshot.result.name
Invoke-WebRequest `
  -Uri "http://localhost:6333/collections/doctrinal_chunks_v1/snapshots/$snapshotName" `
  -OutFile "$backupDir/$snapshotName"
Get-FileHash "$backupDir/$snapshotName" -Algorithm SHA256
```

Restore only into a temporary collection:

```powershell
curl.exe -X POST `
  -F "snapshot=@$backupDir/$snapshotName" `
  "http://localhost:6333/collections/doctrinal_chunks_v1_phase25_restore/snapshots/upload?priority=snapshot"
Invoke-RestMethod "http://localhost:6333/collections/doctrinal_chunks_v1_phase25_restore"
Invoke-RestMethod -Method Delete "http://localhost:6333/collections/doctrinal_chunks_v1_phase25_restore"
```

The production collection remains `doctrinal_chunks_v1`. If a snapshot is not
available, vectors can be rebuilt from PostgreSQL chunks after OpenAI quota and
credentials are available.

## MinIO

Local object verification:

```powershell
docker compose exec -T minio sh -c "mc alias set local http://localhost:9000 minio miniosecret >/dev/null && mc stat local/gospel-library-assets"
docker compose exec -T minio sh -c "mc alias set local http://localhost:9000 minio miniosecret >/dev/null && mc find local/gospel-library-assets | wc -l"
```

Verify a sample with `mc stat` and `mc cat --offset 0 --length 1024`. Production
must enable R2 bucket versioning, lifecycle rules, and periodic restore drills.

## Resume services

```powershell
docker compose up -d scraper-scheduler scraper-worker-scraping scraper-worker-assets scraper-worker-ocr scraper-worker-indexing rag-worker-indexing
docker compose ps
```

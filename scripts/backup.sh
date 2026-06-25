#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "=== EMSoft Support - Backup ==="

# PostgreSQL
if docker compose -f infra/docker-compose.prod.yml ps postgres &>/dev/null; then
  echo "Backing up PostgreSQL..."
  docker compose -f infra/docker-compose.prod.yml exec -T postgres \
    pg_dump -U emsoft emsoft > "$BACKUP_DIR/postgres_$DATE.sql"
  gzip "$BACKUP_DIR/postgres_$DATE.sql"
  echo "  -> $BACKUP_DIR/postgres_$DATE.sql.gz"
fi

# Qdrant
if [ -d "docker-data/qdrant" ]; then
  echo "Backing up Qdrant..."
  tar -czf "$BACKUP_DIR/qdrant_$DATE.tar.gz" -C docker-data qdrant
  echo "  -> $BACKUP_DIR/qdrant_$DATE.tar.gz"
fi

# MinIO
if [ -d "docker-data/minio" ]; then
  echo "Backing up MinIO..."
  tar -czf "$BACKUP_DIR/minio_$DATE.tar.gz" -C docker-data minio
  echo "  -> $BACKUP_DIR/minio_$DATE.tar.gz"
fi

# SQLite (dev)
if [ -f "backend/dev.db" ]; then
  echo "Backing up SQLite (dev)..."
  cp backend/dev.db "$BACKUP_DIR/dev_$DATE.db"
  gzip "$BACKUP_DIR/dev_$DATE.db"
  echo "  -> $BACKUP_DIR/dev_$DATE.db.gz"
fi

echo "=== Backup complete: $BACKUP_DIR ==="
ls -lh "$BACKUP_DIR"/*"$DATE"* 2>/dev/null

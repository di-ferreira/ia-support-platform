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

# Supabase PostgreSQL (dev local)
if command -v supabase &>/dev/null && supabase status &>/dev/null; then
  echo "Backing up Supabase PostgreSQL..."
  supabase db dump -f "$BACKUP_DIR/supabase_$DATE.sql" 2>/dev/null || \
    pg_dump -h localhost -p 54322 -U postgres postgres > "$BACKUP_DIR/supabase_$DATE.sql"
  gzip "$BACKUP_DIR/supabase_$DATE.sql"
  echo "  -> $BACKUP_DIR/supabase_$DATE.sql.gz"
fi

echo "=== Backup complete: $BACKUP_DIR ==="
ls -lh "$BACKUP_DIR"/*"$DATE"* 2>/dev/null

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${1:-infra/.env.prod}"
COMPOSE_FILE="infra/docker-compose.prod.yml"

echo "=== Starting EMSoft Support - Production ==="
echo "Using compose file: $COMPOSE_FILE"
echo "Using env file: $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Environment file $ENV_FILE not found."
  echo "Copy infra/.env.example to $ENV_FILE and configure it."
  exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" pull

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

echo "Waiting for database..."
sleep 5

echo "Running migrations..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

echo "=== Deployment complete ==="
echo "Frontend: https://app.emsoft.app"
echo "Backend:  https://api.emsoft.app"
echo "n8n:      https://n8n.emsoft.app"
echo "MinIO:    http://localhost:9001"

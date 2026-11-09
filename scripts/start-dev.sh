#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Starting EMSoft Support - Development (containers) ==="

echo "Starting Appwrite (infra/appwrite)..."
docker compose -f "$ROOT_DIR/infra/appwrite/docker-compose.yml" up -d

echo "Starting infra + backend + frontend (docker compose)..."
docker compose -f "$ROOT_DIR/infra/docker-compose.dev.yml" up -d --build

FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' "$ROOT_DIR/infra/.env" 2>/dev/null | cut -d= -f2)"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Credenciais do Appwrite (necessárias para seed e login)
if grep -qE '^[[:space:]]*APPWRITE_PROJECT_ID=(\s*)?$' "$ROOT_DIR/backend/.env"; then
    echo "AVISO: APPWRITE_PROJECT_ID ausente em backend/.env."
    echo "  → Crie um project no console (http://localhost:8020) e preencha o .env."
fi
if grep -qE '^[[:space:]]*APPWRITE_API_KEY=(\s*)?$' "$ROOT_DIR/backend/.env"; then
    echo "AVISO: APPWRITE_API_KEY ausente em backend/.env."
    echo "  → Gere uma API key (papel Database) no console e preencha o .env."
fi

echo ""
echo "Frontend: http://localhost:${FRONTEND_PORT}"
echo "Backend:  http://localhost:8001"
echo "Docs:     http://localhost:8001/docs"
echo "Appwrite: http://localhost:8020"
echo "n8n:      http://localhost:5678"
echo ""
echo "Para parar a stack: docker compose -f infra/docker-compose.dev.yml stop"

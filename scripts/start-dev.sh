#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Starting EMSoft Support - Development ==="

echo "Starting Appwrite (infra/appwrite)..."
docker compose -f "$ROOT_DIR/infra/appwrite/docker-compose.yml" up -d

echo "Starting infra services (redis, qdrant, n8n, evolution)..."
docker compose -f "$ROOT_DIR/infra/docker-compose.dev.yml" up -d

# Credenciais do Appwrite (necessárias para seed e login)
if grep -qE '^[[:space:]]*APPWRITE_PROJECT_ID=(\s*)?$' "$ROOT_DIR/backend/.env"; then
    echo "AVISO: APPWRITE_PROJECT_ID ausente em backend/.env."
    echo "  → Crie um project no console (http://localhost:8020) e preencha o .env."
fi
if grep -qE '^[[:space:]]*APPWRITE_API_KEY=(\s*)?$' "$ROOT_DIR/backend/.env"; then
    echo "AVISO: APPWRITE_API_KEY ausente em backend/.env."
    echo "  → Gere uma API key (papel Database) no console e preencha o .env."
fi

echo "Starting backend (uv run uvicorn)..."
cd "$ROOT_DIR/backend"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!
cd "$ROOT_DIR"

echo "Starting frontend..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8001"
echo "Docs:     http://localhost:8001/docs"
echo "Appwrite: http://localhost:8020"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

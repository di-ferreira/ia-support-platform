#!/usr/bin/env bash
set -euo pipefail

echo "=== Starting EMSoft Support - Development ==="

echo "Starting infra services..."
docker compose -f infra/docker-compose.dev.yml up -d

echo "Starting backend..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

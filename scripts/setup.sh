#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "  EMSoft Support AI - Setup"
echo "============================================"

# ── Appwrite (fonte de dados) ─────────────────────
echo ""
echo "[1/5] Subindo Appwrite (infra/appwrite)..."
cd "$ROOT_DIR"
docker compose -f "$ROOT_DIR/infra/appwrite/docker-compose.yml" up -d
echo "  → Appwrite em http://localhost:8020"

# ── Backend ────────────────────────────────────────
echo ""
echo "[2/5] Configurando backend..."
cd "$ROOT_DIR/backend"
uv sync --quiet
echo "  → Dependências sincronizadas (uv sync)"

# ── Infra dev ─────────────────────────────────────
echo ""
echo "[3/5] Subindo infra dev (redis, qdrant, n8n, evolution)..."
cd "$ROOT_DIR"
docker compose -f "$ROOT_DIR/infra/docker-compose.dev.yml" up -d
echo "  → Containers dev prontos"

# ── Frontend ───────────────────────────────────────
echo ""
echo "[4/5] Configurando frontend..."
cd "$ROOT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install --silent
    echo "  → Dependências instaladas"
else
    echo "  → node_modules já existe, pulando npm install"
fi

if [ ! -f ".env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local
    echo "  → .env.local criado (API em :8001)"
else
    echo "  → .env.local já existe"
fi

# ── Seed Appwrite ──────────────────────────────────
echo ""
echo "[5/5] Seed do Appwrite..."
cd "$ROOT_DIR"
if bash "$ROOT_DIR/scripts/seed.sh"; then
    echo "  → Seed aplicado"
else
    echo "  → Seed adiado: crie o project + API key no console (http://localhost:8020),"
    echo "    preencha APPWRITE_PROJECT_ID / APPWRITE_API_KEY em backend/.env,"
    echo "    e rode ./scripts/seed.sh quando o Appwrite estiver no ar."
fi

# ── Resumo ─────────────────────────────────────────
echo ""
echo "============================================"
echo "  Setup concluído!"
echo "============================================"
echo ""
echo "  Para iniciar o desenvolvimento:"
echo ""
echo "    ./scripts/start-dev.sh"
echo ""
echo "  Acessos:"
echo "    Frontend : http://localhost:3000"
echo "    Backend  : http://localhost:8001/docs"
echo "    Appwrite : http://localhost:8020"
echo ""
echo "  Credenciais (seed):"
echo "    admin@emsoft.app / admin123    (admin)"
echo ""

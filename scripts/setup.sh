#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "  EMSoft Support AI - Setup"
echo "============================================"

# ── Backend ──────────────────────────────────────
echo ""
echo "[1/4] Configurando backend..."

cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  → Virtual environment criado em backend/.venv"
fi

source .venv/bin/activate
echo "  → Python: $(which python3) ($(python3 --version))"

pip install -q -r requirements.txt
echo "  → Dependências instaladas"

alembic upgrade head
echo "  → Migrations aplicadas"

python3 -c "
import asyncio
from app.core.database import async_session, engine, Base
from app.core.security import hash_password

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        from sqlalchemy import text
        from app.models.atendente import Atendente
        result = await session.execute(text('SELECT COUNT(*) FROM atendente'))
        if result.scalar() == 0:
            session.add(Atendente(nome='Admin', email='admin@emsoft.app', hash_senha=hash_password('admin123'), perfil='admin', ativo=True))
            session.add(Atendente(nome='Suporte', email='suporte@emsoft.app', hash_senha=hash_password('suporte123'), perfil='atendente', ativo=True))
            await session.commit()
            print('  → Seed: admin + suporte criados')
        else:
            print('  → Seed ignorado — dados já existem')

asyncio.run(seed())
" 2>&1 | grep -v "^INFO\|^$"

# ── Frontend ─────────────────────────────────────
echo ""
echo "[2/4] Configurando frontend..."

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

# ── Infra ────────────────────────────────────────
echo ""
echo "[3/4] Verificando infraestrutura..."

cd "$ROOT_DIR"

if docker compose -f infra/docker-compose.dev.yml ps --status running 2>/dev/null | grep -q "redis"; then
    echo "  → Containers já rodando"
else
    echo "  → Subindo containers (Redis, Qdrant, n8n, Postgres)..."
    docker compose -f infra/docker-compose.dev.yml up -d
fi

# ── Resumo ───────────────────────────────────────
echo ""
echo "============================================"
echo "  Setup concluído!"
echo "============================================"
echo ""
echo "  Para iniciar o desenvolvimento:"
echo ""
echo "    source backend/.venv/bin/activate"
echo "    scripts/start-dev.sh"
echo ""
echo "  Acessos:"
echo "    Frontend : http://localhost:3000"
echo "    Backend  : http://localhost:8001/docs"
echo "    Portainer: https://localhost:9443"
echo ""
echo "  Credenciais:"
echo "    admin@emsoft.app / admin123    (admin)"
echo "    suporte@emsoft.app / suporte123 (atendente)"
echo ""

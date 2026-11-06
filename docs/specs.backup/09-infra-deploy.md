# SPEC 09 — Infraestrutura e deploy

Ambientes, topologia de containers, segredos, persistência, backup, deploy e CI.
Requisitos não funcionais que atravessam o sistema ficam em
[08-non-functional.md](08-non-functional.md); estratégia de teste em
[10-test-strategy.md](10-test-strategy.md).

## Decisão arquitetural

A stack é **100% Docker Compose**, em três pilhas independentes:

- **Dev** — `infra/docker-compose.dev.yml`: Redis, Qdrant, n8n, Evolution API + banco. O
  backend **não** roda em container: sobe na máquina via `uvicorn` (`scripts/start-dev.sh`).
- **Prod** — `infra/docker-compose.prod.yml`: Traefik + backend + frontend + Postgres +
  Redis + Qdrant + MinIO + n8n + Evolution API.
- **Appwrite** — `infra/appwrite/docker-compose.yml`: self-hosted completo (API, console,
  realtime, workers, Mongo, ClickHouse), com Traefik próprio. **Não faz parte da pilha prod.**

O Appwrite é a **store primária** de dados (`seed_appwrite.py`, repositórios,
`ensure_appwrite_schema`) — mas a pilha prod não o sobe nem o referencia. Ver gap **09-1**.

## Topologia dev

| Serviço | Imagem | Porta (host) | Observação |
|---|---|---|---|
| Redis | redis:7-alpine | 6379 | cache / memória de chat |
| Qdrant | qdrant/qdrant:latest | 6333/6334 | vetores RAG |
| n8n | n8nio/n8n:latest | 5678 | orquestração (webhook Evolution → backend) |
| Evolution API | evoapicloud/evolution-api:latest | 8080 | WhatsApp |
| evolution-db | postgres:16-alpine | interno | dados da Evolution |

- Backend: `uvicorn app.main:app --port 8001` na máquina (`start-dev.sh`), com
  `APPWRITE_ENDPOINT=http://127.0.0.1:8020/v1`.
- Frontend: `npm run dev` na porta 3000.
- Appwrite: console na porta **8020** (stack própria, rede isolada da dev).
- Segredos: `infra/.env.example` é a fonte; `start-dev.sh` carrega de `.env`.

## Topologia prod

| Serviço | Imagem | Roteamento Traefik | Observação |
|---|---|---|---|
| Traefik | traefik:v3.1 | 80 → 443 (Let's Encrypt http challenge) | `infra/traefik/traefik.yml` |
| Backend | build `backend/` | `api.emsoft.app` → :8000 | `ENVIRONMENT=production` |
| Frontend | build `frontend/` | `app.emsoft.app` → :3000 | `NEXT_PUBLIC_API_URL=https://api.emsoft.app` |
| Postgres | postgres:16-alpine | — (interno) | `emsoft`/`emsoft`/`emsoft` |
| Redis | redis:7-alpine | — (interno) | cache |
| Qdrant | qdrant/qdrant:latest | — (interno) | sem porta exposta |
| MinIO | minio/minio:latest | — (interno) | **órfão** — ver gap 09-3 |
| n8n | n8nio/n8n:latest | `n8n.emsoft.app` | `N8N_HOST` / `N8N_PROTOCOL=https` |
| Evolution API | evoapicloud/evolution-api:latest | `evolution.emsoft.app` | usa Postgres + Redis do compose |

- A pilha prod **não** sobe Appwrite nem serviço de LLM (Ollama) — ver gaps **09-1** e **09-15**.
- `depends_on` do backend espera só Postgres (healthy) e Redis — não Qdrant, Appwrite nem Evolution.
- `CORS_ORIGINS` default é `http://localhost:3000`; a pilha prod **não** o sobrepõe (gap 08-1, **09-2**).

## Segredos e configuração

| Variável | Onde é esperada | Presente na pilha prod? |
|---|---|---|
| `SECRET_KEY` | backend | **não** (o boot bloquearia com o default) |
| `APPWRITE_ENDPOINT` / `APPWRITE_PROJECT_ID` / `APPWRITE_API_KEY` | backend | **não** (default `http://127.0.0.1:8020/v1`) |
| `WEBHOOK_SECRET` | backend + n8n | n8n sim, backend **não** |
| `EVOLUTION_API_URL` / `EVOLUTION_API_KEY` | backend + n8n + Evolution | sim |
| `DATABASE_URL_PROD` | backend (schema legado) | sim |
| `QDRANT_URL` | backend | **não** (default `http://localhost:6333`, inatingível no container) |
| `OLLAMA_URL` / `OLLAMA_MODEL` / `OLLAMA_EMBED_MODEL` | backend | **não** (sem serviço Ollama no compose) |
| `CORS_ORIGINS` | backend | **não** (default localhost) |

O bloco de `environment` do backend prod (`infra/docker-compose.prod.yml`) passa apenas
`ENVIRONMENT`, `DATABASE_URL_PROD`, `REDIS_URL`, `MINIO_*` e `EVOLUTION_API_*`. O restante
fica no default de `config.py`, vários dos quais são `localhost` — inatingíveis de dentro do
container. Ver gap **09-2**.

## Persistência

Volumes named: `postgres-data`, `redis-data`, `qdrant-data` (declarados na pilha prod);
`minio-data`, `n8n-data`, `traefik-data` (usados, não declarados — Docker os cria).
O Appwrite mantém os próprios volumes (`appwrite-imports`, Mongo, ClickHouse) na sua pilha.

## Backup

`scripts/backup.sh`:

- **Postgres** — `pg_dump` do container (OK para o schema legado/Evolution).
- **Qdrant** — cópia do diretório `docker-data/qdrant`. **Não funciona em prod**: a pilha
  usa volume named `qdrant-data`, não bind mount. Ver gap **09-5**.
- **Supabase** — bloco remanescente (`supabase db dump`); o Supabase não é mais store. Gap **09-6**.
- **Ausente** — Appwrite (store primária), n8n (workflows/credenciais em `n8n-data`) e
  evolution-db. Gap **09-6**.
- **Agenda** — nenhum cron/systemd/tarefa aponta para `backup.sh`. Gap **09-7**.

## Deploy e operações

- `scripts/start-prod.sh`: `docker compose -f infra/docker-compose.prod.yml pull && up -d`,
  `sleep 5` (em vez de healthcheck) e `alembic upgrade head`. Segredos de `infra/.env.prod`.
- `scripts/migrate.sh`: `alembic upgrade head` no diretório do backend.
- **Alembic/Postgres híbrido** — o runtime usa Appwrite, mas `seed_qdrant.py` e o Alembic
  ainda leem/escrevem o Postgres `emsoft` (`KnowledgeBase`); `DATABASE_URL_PROD` serve esse
  schema legado **e** a Evolution API. Ver gap **09-12** e gap 02-14.
- **Seed** — `scripts/seed.sh` → `seed_appwrite.py` (schema + 1º atendente);
  `seed_qdrant.py` indexa o corpus na Qdrant (gap 02-14: lê do Postgres, não do Appwrite).

### Runbook — trocar o modelo de embedding (ADR-0005)

1. Criar coleção nova com a nova `VECTOR_SIZE`.
2. Re-executar o seed de indexação com o **mesmo** modelo que o backend usará.
3. Apontar `qdrant_service.py` para a coleção nova (mesmo PR: constante + seed + coleção).
4. Validar busca e só então trocar o tráfego; reter a coleção antiga até validação.
5. `LLM_PROVIDER=openai` segue **bloqueado** para RAG até existir a coleção 1536 (gap 05-11).

## CI

`.github/workflows/ci.yml` — três jobs:

- **Backend** — uv Python 3.11, `uv lock --check`, `uv sync --frozen --extra dev`,
  `ruff check app tests`, `mypy app/ --ignore-missing-imports || true` (report-only),
  `pytest tests/ -q`.
- **Frontend** — Node 22, `npm ci`, `npm run lint || true` (report-only), `npm run build`.
- **Docker** — buildx `build` das imagens backend e frontend (`push: false`).

Sem job de teste do frontend e com lint/mypy não bloqueantes. Ver gaps **09-13**/09-14.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 09-1 | Appwrite (store primária) **ausente** da pilha prod: não é sobido nem referenciado; backend prod aponta para `127.0.0.1:8020` (inexistente) | `docker-compose.prod.yml`; `config.py:13` | **Crítica** | **ABERTO** |
| 09-2 | Bloco de env do backend prod incompleto: faltam `SECRET_KEY`, `APPWRITE_*`, `WEBHOOK_SECRET`, `QDRANT_URL`, `OLLAMA_*`, `CORS_ORIGINS` — defaults `localhost` inatingíveis no container | `docker-compose.prod.yml`; `config.py` | **Crítica** | **ABERTO** |
| 09-3 | MinIO órfão: serviço + `MINIO_*` no compose prod, mas zero referências em `backend/app/` | `docker-compose.prod.yml` | Baixa | **ABERTO** |
| 09-4 | Pilha do Appwrite tem rede isolada: backend do compose prod não o alcança por nome mesmo com env correta | `infra/appwrite/` vs `docker-compose.prod.yml` | **Alta** | **ABERTO** |
| 09-5 | Backup Qdrant usa bind mount `docker-data/qdrant`; prod usa volume named `qdrant-data` — backup não pega nada em prod | `backup.sh` | **Alta** | **ABERTO** |
| 09-6 | Sem backup de Appwrite (store primária), n8n nem evolution-db; bloco Supabase remanescente | `backup.sh` | **Alta** | **ABERTO** |
| 09-7 | `backup.sh` não é agendado em lugar nenhum (cron/systemd/tarefa) | `scripts/` | **Alta** | **ABERTO** |
| 09-8 | Senha do Postgres em claro no compose prod (`emsoft`) e na string da Evolution | `docker-compose.prod.yml` | Média | **ABERTO** |
| 09-9 | Drift Python: `pyproject`/ruff/mypy/CI em 3.11, mas `Dockerfile` `python:3.12-slim` | `pyproject.toml`; `backend/Dockerfile`; `ci.yml` | Baixa | **ABERTO** |
| 09-10 | Drift de modelo Ollama: `config.py` `llama3.2`, `infra/.env.example` `deepseek-v4-flash:cloud`, n8n `nemotron-3-super:cloud` | `config.py:31`; `infra/.env.example:26`; `workflow-support-ai.json` | Média | **ABERTO** → 05-14 |
| 09-11 | `infra/.env.prod` **não** é gitignored (`.gitignore` cobre `.env*` mas não `infra/.env.prod`) — risco de commit de segredos | `.gitignore` | **Alta** | **ABERTO** |
| 09-12 | Alembic/Postgres híbrido: runtime em Appwrite, mas `seed_qdrant.py` e Alembic ainda usam o Postgres `emsoft`; `DATABASE_URL_PROD` serve esse schema legado | `alembic/env.py`; `seed_qdrant.py`; `config.py:44` | Média | **ABERTO** → 02-14 |
| 09-13 | Env do n8n `BACKEND_URL`/`EVOLUTION_INSTANCE` e `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` ausentes de compose e `.env.example` — `{{ $env.* }}` do workflow falha | `docker-compose.*.yml`; `workflow-support-ai.json` | **Alta** | **ABERTO** → 06-4/06-5 |
| 09-14 | CI: mypy e lint do frontend são report-only (`\|\| true`); nenhum job de teste do frontend | `ci.yml` | Média | **ABERTO** → 10-test-strategy |
| 09-15 | Sem serviço de LLM (Ollama) na pilha prod e sem `OLLAMA_URL` — RAG/LLM inatingíveis no backend prod | `docker-compose.prod.yml`; `config.py:26` | **Crítica** | **ABERTO** |
| 09-16 | `start-prod.sh`: `sleep 5` em vez de aguardar healthcheck; `depends_on` do backend não cobre Qdrant/Appwrite | `start-prod.sh`; `docker-compose.prod.yml` | Baixa | **ABERTO** |

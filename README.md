# EMSoft Support AI Platform

Plataforma SaaS de atendimento WhatsApp com IA para suporte técnico do ERP EMSoft
(autopeças). Reduza em até 70% a carga operacional do suporte humano.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| **Frontend** | Next.js 15, Tailwind CSS 4, React Query, Zustand |
| **Banco Dev** | SQLite (via aiosqlite) |
| **Banco Prod** | PostgreSQL (via asyncpg) |
| **Migrations** | Alembic |
| **Cache** | Redis |
| **Vetores** | Qdrant |
| **Orquestração** | n8n |
| **LLM** | OpenAI (gpt-4o-mini) / Ollama (fallback local) |
| **WhatsApp** | Evolution API |
| **Infra** | Docker, Docker Compose, Traefik |

---

## Quick Start

```bash
# 1. Backend
cd backend
pip install .
cp .env.example .env   # configure if needed
alembic upgrade head
python scripts/seed.sh
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 2. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000

# 3. Infra (Redis, Qdrant, MinIO, n8n)
docker compose -f infra/docker-compose.dev.yml up -d
```

### Credenciais Padrão (dev)

| Email | Senha | Perfil |
|---|---|---|
| `admin@emsoft.app` | `admin123` | Admin |
| `suporte@emsoft.app` | `suporte123` | Atendente |

---

## Estrutura do Projeto

```
├── backend/
│   ├── app/
│   │   ├── ai/              # Módulo de IA (OpenAI, Ollama, prompts)
│   │   ├── api/
│   │   │   ├── routes/      # Endpoints (auth, clientes, chats, etc.)
│   │   │   └── websocket_manager.py
│   │   ├── core/            # Config, database, security
│   │   ├── models/          # SQLAlchemy models (10 tabelas)
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Migrations
│   └── tests/               # Pytest tests
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages (9 páginas)
│       ├── components/      # UI components
│       ├── hooks/           # Custom hooks
│       └── lib/             # API client, stores
├── infra/
│   ├── docker-compose.yml   # Dev services
│   ├── docker-compose.prod.yml
│   ├── traefik/
│   └── n8n/                 # Workflow export
├── scripts/                 # Start, migrate, seed, backup
└── docs/                    # Documentation
```

---

## API (Swagger)

Com o backend rodando, acesse:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/login` | Login (JWT) |
| GET | `/auth/me` | Perfil do usuário |
| GET/POST | `/clientes` | Listar / Criar clientes |
| GET/PATCH | `/clientes/{id}` | Detalhe / Atualizar cliente |
| GET/POST | `/chats` | Listar / Criar chats |
| PATCH | `/chats/{id}/status` | Transicionar status |
| GET/POST | `/chats/{id}/mensagens` | Listar / Enviar mensagens |
| GET | `/kanban` | Kanban com 7 colunas |
| CRUD | `/knowledge-base` | Base de conhecimento |
| POST | `/webhooks/mensagem` | Webhook n8n (mensagem) |
| POST | `/webhooks/chat/diagnostico` | Webhook n8n (diagnóstico IA) |
| POST | `/ai/classificar` | Classificar problema |
| POST | `/ai/sumarizar` | Sumarizar conversa |
| POST | `/ai/diagnosticar` | Diagnóstico completo |
| WS | `/ws/chat/{id}` | WebSocket tempo real |

---

## Chat State Machine

```
NOVO → IA_ANALISANDO
         ├→ AGUARDANDO_CLIENTE
         ├→ AGUARDANDO_HUMANO_COM_SOLUCAO
         └→ AGUARDANDO_HUMANO_SEM_SOLUCAO
                  ↓
            EM_ATENDIMENTO
              ├→ AGUARDANDO_CLIENTE
              ├→ RESOLVIDO → ENCERRADO
              └→ ENCERRADO
```

---

## Fluxo de Atendimento (3 Cenários)

```
Cliente WhatsApp → n8n → API → RAG (Qdrant) → LLM
                                                  ↓
                           ┌──────────────────────┼──────────────────────┐
                      Cenário A             Cenário B              Cenário C
                   IA resolve +          Transferir com          Transferir sem
                   responde cliente      solução para humano    solução para humano
```

---

## Testes

```bash
cd backend
python -m pytest tests/ -v
```

---

## Deploy

```bash
# Produção
./scripts/start-prod.sh

# Backup
./scripts/backup.sh
```

Ver `docs/n8n-workflow.md` para configurar o n8n e o RAG.

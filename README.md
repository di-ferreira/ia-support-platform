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
| **Armazenamento** | MinIO (S3) |
| **Infra** | Docker, Docker Compose, Traefik |

---

## Quick Start

### Pré-requisitos

- Python 3.11+, Node.js 20+, Docker + Docker Compose
- Copiar e configurar variáveis de ambiente:

```bash
cp infra/.env.example infra/.env
# Editar infra/.env com suas chaves (OpenAI, Evolution API, etc.)
```

### 1. Infraestrutura (Redis, Qdrant, MinIO, n8n, Evolution API)

```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

Tudo em uma única stack: Redis, Qdrant, MinIO, n8n e Evolution API.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # configure if needed
alembic upgrade head
python3 -m app.scripts.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
# → http://localhost:8001/docs
```

> A porta 8000 é usada pelo Portainer. O backend usa 8001 por padrão.

### 3. Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local
npm run dev
# → http://localhost:3000
```

### Credenciais Padrão (dev)

| Email | Senha | Perfil |
|---|---|---|
| `admin@emsoft.app` | `admin123` | Admin |
| `suporte@emsoft.app` | `suporte123` | Atendente |

---

## Setup Automático

```bash
./scripts/setup.sh
```

Cria venv, instala dependências, aplica migrations, popula seed,
configura frontend e verifica containers Docker.

---

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
│   │   ├── models/          # SQLAlchemy models (9 tabelas)
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Migrations
│   ├── requirements.txt     # Dependências (fonte canônica)
│   └── tests/               # Pytest (33 testes)
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages (7 páginas)
│       ├── components/      # UI components
│       ├── hooks/           # Custom hooks
│       └── lib/             # API client, stores
├── infra/
│   ├── .env.example         # Template de variáveis de ambiente
│   ├── docker-compose.dev.yml   # Dev (Redis, Qdrant, MinIO, n8n, Evolution)
│   ├── docker-compose.prod.yml  # Prod (+Traefik, PostgreSQL)
│   ├── traefik/
│   └── n8n/                 # Workflow export
├── scripts/                 # setup, start-dev, start-prod, migrate, seed, backup
└── docs/                    # Documentation
```

---

## API (Swagger)

Com o backend rodando, acesse:

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

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
| POST | `/ai/analisar?tipo=sumarizar\|diagnosticar` | Sumarizar ou diagnosticar |
| POST | `/ai/solucionar` | Solução com RAG |
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

## Infraestrutura Docker

### Dev (ambiente local)

```bash
# Subir todos os serviços
docker compose -f infra/docker-compose.dev.yml up -d

# Serviços:
#   Redis      → localhost:6379
#   Qdrant     → localhost:6333
#   MinIO      → localhost:9000 (API) / 9001 (Console)
#   n8n        → localhost:5678
#   Evolution  → localhost:8080

# Parar tudo
docker compose -f infra/docker-compose.dev.yml down
```

### Prod (ambiente production)

```bash
# Configurar variáveis
cp infra/.env.example infra/.env
# Editar infra/.env com SECRET_KEY, EVOLUTION_API_KEY, etc.

# Subir produção
./scripts/start-prod.sh

# Backup
./scripts/backup.sh
```

### Variáveis de Ambiente

Copie `infra/.env.example` para `infra/.env` e ajuste:

| Variável | Default (dev) | Obrigatório |
|---|---|---|
| `ENVIRONMENT` | `development` | Sim |
| `SECRET_KEY` | `dev-secret-key...` | Sim (mude em prod) |
| `EVOLUTION_API_KEY` | `evolution_dev_key` | Sim (mude em prod) |
| `OPENAI_API_KEY` | — | Para usar OpenAI |
| `MINIO_ROOT_USER` | `minioadmin` | Opcional |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | Opcional |

---

## Fluxo de Mensagens (WhatsApp)

```
Cliente WhatsApp
       ↓
Evolution API (:8080)  ← recebe mensagem
       ↓
n8n (:5678)            ← webhook, orquestra fluxo
       ↓
Backend API (:8001)    ← salva chat/mensagem
       ↓
Qdrant (:6333)         ← busca RAG na base de conhecimento
       ↓
LLM (OpenAI/Ollama)    ← gera diagnóstico/solução
       ↓
n8n                    ← decide cenário A/B/C
       ↓
Evolution API          ← envia resposta ao cliente
```

Ver `docs/n8n-workflow.md` para detalhes do fluxo.

# EMSoft Support AI Platform

Plataforma SaaS de atendimento WhatsApp com IA para suporte técnico do ERP EMSoft
(autopeças). Reduza em até 70% a carga operacional do suporte humano.

> **Este README é um guia de setup rápido.** A fonte única de verdade — escopo,
> domínio, contrato de API, decisões e registro de gaps — vive em [`docs/specs/`](docs/specs/).
> Em caso de divergência, vale o que está lá.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.11+, FastAPI |
| **Frontend** | Next.js 15, Tailwind CSS 4, React Query, Zustand |
| **Dados** | Appwrite (self-hosted) |
| **Cache** | Redis |
| **Vetores** | Qdrant |
| **Orquestração** | n8n |
| **LLM** | Ollama (alvo local) / OpenAI (só LLM chat, nunca RAG — [ADR-0005](docs/specs/adr/0005-dimensao-de-embedding.md)) |
| **WhatsApp** | Evolution API |
| **Armazenamento** | Appwrite (arquivos/mídia — não existe Supabase na pilha) |
| **Infra** | Docker, Docker Compose, Traefik |

---

## Quick Start

### Pré-requisitos

- Python 3.11+, Node.js 20+, Docker + Docker Compose
- Copiar e configurar variáveis de ambiente:

```bash
cp infra/.env.example infra/.env
# Editar infra/.env com suas chaves (Ollama, Evolution API, etc.)
```

### 1. Appwrite (fonte de dados)

```bash
docker compose -f infra/appwrite/docker-compose.yml up -d
```

- Console: http://localhost:8020
- Crie um **project** e uma **API key** (papel *Database*) no console.
- Copie `backend/.env.example` para `backend/.env` e preencha
  `APPWRITE_PROJECT_ID` e `APPWRITE_API_KEY`.

### 2. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
# → http://localhost:8001/docs
```

> A porta 8000 é usada pelo Portainer. O backend usa 8001 por padrão.

### 3. Seed (primeiro atendente)

```bash
./scripts/seed.sh
```

Cria o schema Appwrite (idempotente) e o 1º atendente admin
(`SEED_ATENDENTE_EMAIL` / `SEED_ATENDENTE_SENHA`, default `admin@emsoft.app` / `admin123`).

### 4. Frontend

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

Sobe o Appwrite e a infra de dev, instala dependências com `uv sync`,
prepara o frontend e roda o seed (best-effort).

---

## Estrutura do Projeto

```
├── backend/
│   ├── app/
│   │   ├── ai/              # Módulo de IA (Ollama alvo; OpenAI bloqueado para RAG, ADR-0005)
│   │   ├── api/
│   │   │   ├── routes/      # Endpoints (auth, clientes, chats, etc.)
│   │   │   └── websocket_manager.py
│   │   ├── appwrite/        # Fonte de dados (schema, bootstrap, repositórios)
│   │   ├── core/            # Config, security
│   │   ├── models/          # (legado) SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # (legado) migrations
│   ├── pyproject.toml       # Dependências (uv, fonte canônica)
│   └── tests/               # Pytest
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       ├── components/      # UI components
│       ├── hooks/           # Custom hooks
│       └── lib/             # API client, stores
├── infra/
│   ├── .env.example             # Template de variáveis de ambiente
│   ├── appwrite/              # Appwrite self-hosted (docker-compose.yml + .env)
│   ├── docker-compose.dev.yml   # Dev (Redis, Qdrant, n8n, Evolution)
│   ├── docker-compose.prod.yml  # Prod (+Traefik)
│   ├── traefik/
│   └── n8n/                     # Workflow export
├── scripts/                 # setup, start-dev, start-prod, seed, backup
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

### Produção

```bash
# Appwrite (fonte de dados)
docker compose -f infra/appwrite/docker-compose.yml up -d

# Aplicação
docker compose -f infra/docker-compose.prod.yml up -d

# Backup
./scripts/backup.sh
```

## Infraestrutura Docker

### Dev (ambiente local)

```bash
# Appwrite (fonte de dados)
docker compose -f infra/appwrite/docker-compose.yml up -d

# Infra de apoio
docker compose -f infra/docker-compose.dev.yml up -d

# Serviços:
#   Appwrite (core + console) → http://localhost:8020
#   Redis                     → localhost:6379
#   Qdrant                    → localhost:6333
#   n8n                       → localhost:5678
#   Evolution                 → localhost:8080

# Parar tudo
docker compose -f infra/docker-compose.dev.yml down
docker compose -f infra/appwrite/docker-compose.yml down
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
| `LLM_PROVIDER` | `ollama` | Sim (alvo local) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Sim (alvo) |
| `OLLAMA_MODEL` | `llama3.2` | LLM chat |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding (768) |
| `OPENAI_API_KEY` | — | Opcional — só LLM chat, nunca RAG ([ADR-0005](docs/specs/adr/0005-dimensao-de-embedding.md)) |

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
LLM (Ollama; OpenAI bloqueado para RAG) ← gera diagnóstico/solução
        ↓
Backend API (:8001)    ← decide cenário A/B/C (regra determinística, ver ADR-0004)
        ↓
Evolution API          ← envia resposta ao cliente
```

O n8n é apenas o orquestrador de transporte: ele não contém prompt de negócio nem decide
o cenário. Ver [`docs/specs/06-n8n-workflow.md`](docs/specs/06-n8n-workflow.md) e
[`docs/specs/05-ai-pipeline.md`](docs/specs/05-ai-pipeline.md) para detalhes do fluxo.

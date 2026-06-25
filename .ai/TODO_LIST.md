# TODO LIST — EMSoft Support AI Platform

> Plataforma SaaS de atendimento WhatsApp com IA para suporte técnico do ERP EMSoft (autopeças).
> Stack: Python (FastAPI) + Next.js + SQLite/PostgreSQL + n8n + RAG + Evolution API

---

## Fase 0 — Fundação & Setup do Projeto ✅

### 0.1 Estrutura do Monorepo
- [x] Criar estrutura de pastas: `backend/`, `frontend/`, `infra/`, `docs/`
- [x] Criar `.gitignore` abrangente (Python, Node, Docker, OS, IDE)
- [x] Configurar `pyproject.toml` no `backend/`
- [x] Configurar `package.json` no `frontend/`

### 0.2 Backend — Python/FastAPI
- [x] Instalar dependências FastAPI, SQLAlchemy async, Alembic, JWT, etc.
- [x] Estrutura inicial: `app/core/{config,security,database}.py`
- [x] Configurar Alembic com suporte a SQLite dev / PostgreSQL prod
- [x] Async engine com switch de URL por ambiente

### 0.3 Frontend — Next.js
- [x] `package.json` com Next.js 15, Tailwind 4, React Query, Zustand
- [x] Tailwind config com design tokens EMSoft (navy `#063778` + orange `#f17318`)
- [x] Layout base e página inicial

### 0.4 Infraestrutura — Docker Compose
- [x] `docker-compose.dev.yml` com Redis, Qdrant, MinIO, n8n
- [x] `docker-compose.prod.yml` com Traefik, backend, frontend, PostgreSQL, Redis, Qdrant, MinIO, n8n
- [x] `infra/.env.example` com todas as variáveis
- [x] Dockerfiles multi-stage para backend (Python) e frontend (Next.js standalone)

### 0.5 Scripts
- [x] `scripts/start-dev.sh` — sobe ambiente dev
- [x] `scripts/migrate.sh` — executa migrations
- [x] `scripts/seed.sh` — popula dados iniciais

---

## Fase 1 — Modelagem do Banco de Dados ✅

### 1.1 Modelos SQLAlchemy
- [x] **Cliente**: id, nome, documento (unique), email, telefone, endereco, versao_erp
- [x] **Loja/Filial**: id, cliente_id (FK), nome, documento, endereco
- [x] **Atendente**: id, nome, email (unique), hash_senha, perfil (admin/supervisor/atendente), ativo
- [x] **Chat**: id, cliente_id, loja_id, atendente_id, status (8 estados), prioridade, resumo_problema, solucao_sugerida_ia, causa_provavel, nivel_confianca_ia, necessita_humano, whatsapp_number
- [x] **Mensagem**: id, chat_id, remetente (cliente/ia/atendente/sistema), tipo (texto/audio/documento/imagem), conteudo, url_arquivo
- [x] **Tag + ChatTag**: N:N entre tags e chats
- [x] **IADiagnostico**: id, chat_id, status_ia, resumo, solucao, causa_provavel, confianca, modelo, tokens
- [x] **Historico**: id, chat_id, campo_alterado, valor_anterior, valor_novo, alterado_por
- [x] **KnowledgeBase**: id, titulo, conteudo, categoria (fiscal/estoque/compras/vendas/financeiro), tipo_arquivo, url_arquivo, ativo

### 1.2 Migrations
- [x] `alembic.ini` + `env.py` com autogenerate
- [x] Migration `initial_schema` com todas as 10 tabelas
- [x] Seed: Admin (admin@emsoft.app) e Suporte (suporte@emsoft.app)

### 1.3 Índices e Constraints
- [x] Índices em `chat.status`, `chat.cliente_id`, `mensagem.chat_id`, `mensagem.created_at`
- [x] Foreign keys com cascade onde apropriado
- [x] Unique: `atendente.email`, `cliente.documento`

---

## Fase 2 — Backend API (FastAPI) ✅

### 2.1 Core
- [x] **Config**: `pydantic-settings` carregando de `.env`
- [x] **Database**: AsyncSession factory, dependency injection
- [x] **Security**: JWT (access + refresh token), bcrypt, dependências `get_current_user`
- [x] **Middleware**: CORS configurado
- [x] **WebSocket manager**: `ConnectionManager` em `app/api/websocket_manager.py`

### 2.2 Auth
- [x] `POST /auth/login` — retorna JWT
- [x] `POST /auth/refresh` — renova token
- [x] `GET /auth/me` — perfil do usuário logado
- [x] `PATCH /auth/password` — trocar senha

### 2.3 Clientes
- [x] `GET /clientes` — listar com paginação e filtros (nome/documento)
- [x] `GET /clientes/{id}` — detalhe com lojas
- [x] `POST /clientes` — criar (com validação de duplicidade)
- [x] `PATCH /clientes/{id}` — atualizar
- [x] `GET /clientes/{id}/lojas` — lojas/filiais do cliente
- [x] `POST /clientes/{id}/lojas` — adicionar loja

### 2.4 Chats (State Machine)
- [x] `GET /chats` — listar com filtros (status, cliente, prioridade)
- [x] `GET /chats/{id}` — detalhe com mensagens e diagnóstico IA
- [x] `POST /chats` — criar novo chat
- [x] `PATCH /chats/{id}/status` — transicionar status com validação de máquina de estados
- [x] `PATCH /chats/{id}/assinar` — atribuir a atendente
- [x] `PATCH /chats/{id}/prioridade` — alterar prioridade
- [x] Validação de transições: `STATUS_TRANSITIONS` definindo fluxo completo

### 2.5 Mensagens
- [x] `GET /chats/{id}/mensagens` — listar mensagens do chat
- [x] `POST /chats/{id}/mensagens` — enviar mensagem (texto)
- [ ] `POST /chats/{id}/mensagens/midia` — enviar mídia (upload para MinIO)
- [ ] `GET /mensagens/{id}/arquivo` — download de arquivo

### 2.6 Kanban
- [x] `GET /kanban` — 7 colunas com cards agregados por status
- [x] `PATCH /kanban/mover` — mover card entre colunas

### 2.7 Knowledge Base
- [x] `GET /knowledge-base` — listar artigos (filtro por categoria)
- [x] `GET /knowledge-base/{id}` — detalhe do artigo
- [x] `POST /knowledge-base` — criar artigo
- [x] `PATCH /knowledge-base/{id}` — atualizar
- [x] `DELETE /knowledge-base/{id}` — remover

### 2.8 Webhooks (para n8n)
- [x] `POST /webhooks/mensagem` — n8n envia mensagem (cria chat se não existir)
- [x] `PATCH /webhooks/chat/status` — n8n atualiza status
- [x] `POST /webhooks/chat/diagnostico` — injeta resumo + solução da IA + cria registro de diagnóstico
- [x] `GET /webhooks/chat/{id}/contexto` — n8n consulta estado do chat + última mensagem

### 2.9 WebSocket
- [x] `WS /ws/chat/{chat_id}` — conexão bidirecional, broadcast para múltiplos clientes

### 2.10 OpenAPI
- [x] Swagger automático em `/docs` (FastAPI nativo)
- [x] Tags organizadas por módulo (Autenticação, Clientes, Chats, Kanban, etc.)

---

## Fase 3 — Frontend (Next.js) ✅

### 3.1 Setup
- [x] Tailwind config com design tokens EMSoft (navy `#063778` + orange `#f17318`)
- [x] React Query com `QueryClientProvider` + refetch automático
- [x] Zustand stores: `auth-store` (token/user), `chat-store` (chats/chatAtivo)
- [x] WebSocket manager no backend (`/ws/chat/{chat_id}`) — frontend escutando
- [x] Layout base: `Sidebar` (8 links + perfil + logout) + `Header` (notificações + avatar)
- [x] Providers wrapper em `RootLayout`

### 3.2 Autenticação
- [x] Tela de login com validação e redirect pós-login
- [x] JWT armazenado em `localStorage` + enviado via `Authorization: Bearer`
- [x] Guard de rotas via `(app)/layout.tsx` — redirect para /login se não autenticado
- [x] Sidebar com nome + perfil + botão de logout

### 3.3 Dashboard
- [x] 6 KPI cards: Total Chamados, Resolvidos IA, Transbordo, Tempo Médio, Taxa IA, Críticos
- [x] Gráfico de distribuição por status (barras horizontais com badge)
- [x] Tabela de chamados recentes (5 últimos com prioridade)

### 3.4 Kanban
- [x] 7 colunas: Novos, IA Analisando, Com Solução, Sem Solução, Em Atendimento, Aguardando Cliente, Resolvidos
- [x] Cards com: nome cliente, resumo, prioridade (badge colorido), IA confidence
- [x] Drag-and-drop nativo (HTML5 DnD) com atualização via API
- [x] Contador de cards por coluna
- [x] Indicador de urgência via badge de prioridade + label "Sem Solução"

### 3.5 Atendimento (WhatsApp Inbox)
- [x] Sidebar esquerda: lista de conversas com nome, status, prioridade, indicador IA
- [x] Chat central: bolhas de mensagem (cliente/atendente/IA com cores diferentes)
- [x] Input de texto com botão de envio
- [x] **Painel direito**: Resumo, Causa Provável, Solução Sugerida, Nível de Confiança (barra %)
- [x] Estado vazio "Selecione uma conversa"

### 3.6 CRM — Cliente
- [x] Lista de clientes com busca por nome
- [x] Detalhe do cliente: documento, email, telefone, versão ERP, lojas/filiais
- [x] Chamados recentes do cliente com status e prioridade

### 3.7 Knowledge Base
- [x] Grid de categorias: Fiscal, Estoque, Compras, Vendas, Financeiro (badges coloridos)
- [x] Filtro por categoria + busca por título
- [x] Cards de artigo: título, conteúdo (line-clamp), tipo de arquivo

### 3.8 IA Dashboard
- [x] KPIs: Taxa de Resolução IA, Sugestões Feitas, Resolvidos pela IA, Confiança Média, Sem Solução
- [x] Distribuição por status (kanban aggregate)

### 3.9 Relatórios
- [x] 8 cards de acesso rápido: Volume, SLA, CSAT/NPS, Performance Equipe/IA, Categorias, Tendências, Relatório Completo

### 3.10 Configurações
- [x] 8 seções: WhatsApp, SLA, Equipe, Notificações, Categorias, IA, Integrações, Gerais

---

## Fase 4 — Orquestração n8n (com RAG) ✅

### 4.1 Fluxo Principal — Recebimento de Mensagem
- [x] Webhook da Evolution API → n8n (`POST /webhook/emsoft-whatsapp`)
- [x] Extrair número WhatsApp, conteúdo, tipo do payload
- [x] Nó HTTP: `GET /webhooks/chat/{whatsapp}/contexto` (cria se não existir)
- [x] IF Node: chat existe → salvar mensagem / não existe → criar + salvar

### 4.2 Fluxo Principal — Consulta IA + RAG
- [x] IF Node: verifica se IA deve analisar (status NOVO/IA_ANALISANDO/AGUARDANDO_CLIENTE)
- [x] Nó Qdrant: busca vetorial na coleção `emsoft-knowledge-base` (limite 5)
- [x] Nó LLM Chain (OpenAI/Ollama) com prompt JSON estruturado
- [x] Nó Set: parse do JSON de saída da IA em campos individuais

### 4.3 Fluxo Principal — Atualização via API
- [x] Nó HTTP: `POST /webhooks/chat/diagnostico` com diagnóstico completo
- [x] Switch Node: roteia para Cenário A/B/C baseado em `status_ia`

### 4.4 Fluxo Condicional — Cenários
- [x] **Cenário A** (RESOLVIDO_PELA_IA): PATCH status → RESOLVIDO + Evolution API
- [x] **Cenário B** (TRANSFERIR_COM_SOLUCAO): PATCH → AGUARDANDO_HUMANO_COM_SOLUCAO
- [x] **Cenário C** (TRANSFERIR_SEM_SOLUCAO): PATCH → AGUARDANDO_HUMANO_SEM_SOLUCAO

### 4.5 Configuração de RAG no n8n
- [x] Workflow JSON exportável em `infra/n8n/workflow-support-ai.json` (19 nós)
- [x] Documentação completa em `docs/n8n-workflow.md` (arquitetura, nós, variáveis, testes)
- [x] Pipeline de ingestão: upload → extrair texto → chunking (500/50 tokens) → embedding → Qdrant
- [x] Estratégia de chunking + metadados (categoria, título, fonte, data)
- [x] Script de ingestão em massa + instruções de setup

---

## Fase 5 — Integração LLM (IA Generativa) ✅

### 5.1 Módulo app/ai/
- [x] `OpenAIService`: chat completion, chat_json, embed (text-embedding-3-small)
- [x] `OllamaService`: fallback local (llama3.2, nomic-embed-text)
- [x] `AICache`: cache via Redis com TTL de 1h (chave SHA256 do prompt + modelo)
- [x] Fallback automático: se `OPENAI_API_KEY` configurada → OpenAI, senão → Ollama

### 5.2 Endpoints Auxiliares
- [x] `POST /ai/classificar` — classifica o problema em categoria ERP + confiança
- [x] `POST /ai/sumarizar` — sumariza o histórico completo do chat
- [x] `POST /ai/diagnosticar` — diagnóstico completo (categoria, causa, solução, urgência)
- [x] `POST /ai/solucionar` — gera solução com contexto RAG da base de conhecimento

### 5.3 Sistema de Prompts
- [x] Template CLASSIFY_SYSTEM: classificação em 7 categorias ERP com subcategoria
- [x] Template SUMMARIZE_SYSTEM: resumo com problema, tentativas, situação
- [x] Template SOLUTION_SYSTEM: solução com contexto RAG + instruções + referência
- [x] Template DIAGNOSE_SYSTEM: diagnóstico completo com urgência e confiança

---

## Fase 6 — Docker & Deploy

### 6.1 Dockerfiles
- [ ] `backend/Dockerfile` — multi-stage (builder com dependências, runtime slim)
- [ ] `frontend/Dockerfile` — multi-stage (build Next.js, standalone server)

### 6.2 Docker Compose Produção
- [ ] `docker-compose.prod.yml` com todos os serviços
- [ ] Volumes persistentes para PostgreSQL, Qdrant, MinIO, Redis
- [ ] Healthchecks em cada serviço
- [ ] Restart policies (unless-stopped)

### 6.3 Traefik
- [ ] Configuração com entradas dinâmicas
- [ ] SSL automático via Let's Encrypt
- [ ] Rate limiting
- [ ] Headers de segurança

### 6.4 Scripts
- [ ] `scripts/start-dev.sh` — levanta ambiente dev
- [ ] `scripts/start-prod.sh` — levanta produção
- [ ] `scripts/migrate.sh` — executa migrations Alembic
- [ ] `scripts/seed.sh` — popula dados de desenvolvimento
- [ ] `scripts/backup.sh` — backup PostgreSQL + Qdrant + MinIO

---

## Fase 7 — Testes & Finalização

### 7.1 Testes Backend (Pytest)
- [ ] Configurar `pytest-asyncio`, `httpx.AsyncClient`, banco SQLite em memória
- [ ] Testes unitários: models, validação de state machine, schemas
- [ ] Testes de API: todos os endpoints (auth, clientes, chats, mensagens, kanban, webhooks)
- [ ] Testes de integração: fluxo completo chat + IA + webhook

### 7.2 Testes Frontend
- [ ] Vitest: testes de hooks, stores Zustand, utils
- [ ] Playwright: testes E2E (login, kanban, chat, configurações)

### 7.3 Documentação
- [ ] `README.md` — visão geral, stack, instruções de setup, arquitetura
- [ ] `docs/ARCHITECTURE.md` — diagrama de arquitetura, fluxo de dados, decisões
- [ ] `docs/API.md` — documentação da API (ou link para Swagger)
- [ ] `docs/DEPLOY.md` — instruções de deploy em produção

### 7.4 CI/CD (GitHub Actions)
- [ ] Workflow de lint + typecheck + testes no backend
- [ ] Workflow de lint + build + testes no frontend
- [ ] Workflow de build das imagens Docker

---

## Legenda

- `[ ]` — Tarefa a fazer
- `[x]` — Tarefa concluída
- `~` — Tarefa em andamento

## Prioridades

| Prioridade | Fases |
|------------|-------|
| 🔴 Crítica | Fase 0, 1, 2 (Core funcional) |
| 🟡 Alta | Fase 3, 4 (Frontend + n8n) |
| 🟢 Média | Fase 5, 6 (IA + Deploy) |
| 🔵 Baixa | Fase 7 (Testes + Documentação) |

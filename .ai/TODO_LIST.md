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

## Fase 2 — Backend API (FastAPI)

### 2.1 Core
- [ ] **Config**: `pydantic-settings` carregando de `.env`
- [ ] **Database**: AsyncSession factory, dependency injection
- [ ] **Security**: JWT (access + refresh token), bcrypt, dependências `get_current_user`
- [ ] **Middleware**: CORS, logging, request ID
- [ ] **Exception handlers**: Tratamento global de erros
- [ ] **WebSocket manager**: Gerenciar conexões por chat para tempo real

### 2.2 Auth
- [ ] `POST /auth/login` — retorna JWT
- [ ] `POST /auth/refresh` — renova token
- [ ] `GET /auth/me` — perfil do usuário logado
- [ ] `PATCH /auth/password` — trocar senha

### 2.3 Clientes
- [ ] `GET /clientes` — listar (com paginação, filtro por nome/documento)
- [ ] `GET /clientes/{id}` — detalhe com lojas e chamados recentes
- [ ] `POST /clientes` — criar
- [ ] `PATCH /clientes/{id}` — atualizar
- [ ] `GET /clientes/{id}/lojas` — lojas/filiais do cliente
- [ ] `POST /clientes/{id}/lojas` — adicionar loja

### 2.4 Chats (State Machine)
- [ ] `GET /chats` — listar com filtros (status, cliente, prioridade, data)
- [ ] `GET /chats/{id}` — detalhe com mensagens e diagnóstico IA
- [ ] `POST /chats` — criar novo chat
- [ ] `PATCH /chats/{id}/status` — transicionar status (com validação de máquina de estados)
- [ ] `PATCH /chats/{id}/assinar` — atribuir a atendente
- [ ] `PATCH /chats/{id}/prioridade` — alterar prioridade
- [ ] Validação de transições de estado (ex: de NOVO só pode ir para IA_ANALISANDO)

### 2.5 Mensagens
- [ ] `GET /chats/{id}/mensagens` — listar mensagens do chat
- [ ] `POST /chats/{id}/mensagens` — enviar mensagem (texto)
- [ ] `POST /chats/{id}/mensagens/midia` — enviar mídia (upload para MinIO)
- [ ] `GET /mensagens/{id}/arquivo` — download de arquivo

### 2.6 Kanban
- [ ] `GET /kanban` — listar colunas com chamados agregados
- [ ] `PATCH /kanban/mover` — mover card entre colunas

### 2.7 Knowledge Base
- [ ] `GET /knowledge-base` — listar artigos (filtro por categoria)
- [ ] `GET /knowledge-base/{id}` — detalhe do artigo
- [ ] `POST /knowledge-base` — criar (upload de arquivo para MinIO)
- [ ] `PATCH /knowledge-base/{id}` — atualizar
- [ ] `DELETE /knowledge-base/{id}` — remover

### 2.8 Webhooks (para n8n)
- [ ] `POST /webhooks/mensagem` — n8n envia mensagem recebida do WhatsApp
- [ ] `POST /webhooks/chat/status` — n8n atualiza status do chat (IA_ANALISANDO → RESOLVIDO/AGUARDANDO_HUMANO...)
- [ ] `POST /webhooks/chat/diagnostico` — n8n injeta resumo + solução da IA no chat
- [ ] `GET /webhooks/chat/{id}/contexto` — n8n consulta estado atual do chat

### 2.9 WebSocket
- [ ] `WS /ws/chat/{chat_id}` — tempo real: novas mensagens, mudanças de status, digitação
- [ ] Notificar frontend sobre eventos sem polling

### 2.10 OpenAPI
- [ ] FastAPI gera Swagger automaticamente em `/docs`
- [ ] Adicionar descrições e exemplos nos schemas Pydantic

---

## Fase 3 — Frontend (Next.js)

### 3.1 Setup
- [ ] Configurar tema Shadcn/UI com cores do Design System EMSoft
- [ ] Configurar React Query com refetch automático
- [ ] Configurar Zustand para estado global (auth, sidebar, chat ativo)
- [ ] Integrar WebSocket para atualizações em tempo real
- [ ] Criar layout base com sidebar e header responsivo

### 3.2 Autenticação
- [ ] Tela de login com validação
- [ ] Armazenar JWT (httpOnly cookie ou zustand + interceptors)
- [ ] Guard de rotas (redirect para login se não autenticado)
- [ ] Componente de perfil do usuário + logout

### 3.3 Dashboard
- [ ] Cards de KPI (6 métricas: tempo médio, taxa IA, transbordo, chamados/categoria, chamados/cliente, etc.)
- [ ] Gráfico de distribuição de status (pie chart)
- [ ] Gráfico de evolução diária/semanal
- [ ] Status dos atendentes (online/offline/ocupado)
- [ ] Resumo de IA (últimos diagnósticos)
- [ ] Tabela de chamados recentes

### 3.4 Kanban
- [ ] 7 colunas: Novos, IA Analisando, Com Solução, Sem Solução, Em Atendimento, Aguardando Cliente, Resolvidos
- [ ] Cards com: nome cliente, resumo, prioridade, SLA, tempo decorrido, badge de IA
- [ ] Drag-and-drop entre colunas (atualiza status via API)
- [ ] Contador de cards por coluna
- [ ] Indicador visual de urgência (sem solução da IA)

### 3.5 Atendimento (WhatsApp Inbox)
- [ ] Sidebar esquerda: lista de conversas com última mensagem, badge de não lida, indicador IA/humano
- [ ] Chat central: bolhas de mensagem (cliente/atendente/IA), timestamp, áudio player, preview de imagem/documento
- [ ] Input de texto com suporte a anexos
- [ ] **Painel direito**: Resumo da IA + solução sugerida + nível de confiança + timeline de atendimento
- [ ] Botões de ação: Resolver, Transferir, Solicitar IA
- [ ] Indicador de digitação em tempo real (WebSocket)
- [ ] Estado vazio (sem conversas selecionadas)

### 3.6 CRM — Cliente
- [ ] Header com dados do cliente (nome, documento, versão ERP)
- [ ] Tabs: Dados Cadastrais, Contratos, Chamados, NF-e, Financeiro
- [ ] Lista de chamados do cliente com status e datas
- [ ] Endereços e contatos

### 3.7 Knowledge Base
- [ ] Grid de categorias (Fiscal, Estoque, Compras, Vendas, Financeiro)
- [ ] Lista de artigos com busca por título
- [ ] Visualizador de artigo (renderizar markdown/html)
- [ ] CRUD para administradores (criar/editar/excluir artigos)

### 3.8 IA Dashboard
- [ ] KPIs: taxa de resolução, sugestões feitas, tempo médio IA, precisão
- [ ] Gráficos: sugestões por status (aceitas, rejeitadas, pendentes), top categorias resolvidas
- [ ] Tabela de diagnósticos recentes com nível de confiança

### 3.9 Relatórios
- [ ] Cards de acesso rápido: Volume, SLA, CSAT/NPS, Performance Equipe, Performance IA, Categorias, Tendências, Relatório Completo
- [ ] Exportação (PDF/CSV) quando implementado

### 3.10 Configurações
- [ ] Seções: WhatsApp (conexão Evolution API), SLA (tempos por prioridade), Equipe (gerir atendentes), Notificações, Categorias, IA (modelo, prompt), Integrações (n8n, webhooks), Gerais
- [ ] Toggles, inputs, selects para cada configuração

---

## Fase 4 — Orquestração n8n (com RAG)

### 4.1 Fluxo Principal — Recebimento de Mensagem
- [ ] Webhook da Evolution API → n8n
- [ ] Extrair: número WhatsApp, conteúdo da mensagem, tipo, mídia (se houver)
- [ ] Nó HTTP: `GET /webhooks/chat/{id}/contexto` (ou criar/se o chat não existir)
- [ ] Se chat NOVO → criar no banco via `POST /webhooks/mensagem`
- [ ] Se chat existente → adicionar mensagem ao histórico

### 4.2 Fluxo Principal — Consulta IA + RAG
- [ ] Se chat com IA ativa → nó RAG (Qdrant nativo do n8n)
- [ ] Embedding da mensagem do cliente → busca vetorial na base de conhecimento
- [ ] Contexto recuperado → nó OpenAI (ou Ollama) com prompt estruturado
- [ ] Prompt para IA:
  ```
  Você é um especialista em suporte técnico do ERP EMSoft para autopeças.
  Com base no contexto RAG e na mensagem do cliente, classifique:
  1. Status: RESOLVIDO_PELA_IA | TRANSFERIR_COM_SOLUCAO | TRANSFERIR_SEM_SOLUCAO
  2. Resumo do problema
  3. Causa provável
  4. Solução encontrada (se houver)
  5. Nível de confiança (0-100)
  6. Necessita humano (true/false)
  
  Contexto RAG: {{contexto}}
  Mensagem: {{mensagem_cliente}}
  ```

### 4.3 Fluxo Principal — Atualização via API
- [ ] Nó HTTP: `PATCH /webhooks/chat/diagnostico` com JSON de saída da IA
- [ ] Se RESOLVIDO → nó HTTP `PATCH /webhooks/chat/status` → RESOLVIDO
- [ ] Se TRANSFERIR_COM_SOLUCAO → status `AGUARDANDO_HUMANO_COM_SOLUCAO`
- [ ] Se TRANSFERIR_SEM_SOLUCAO → status `AGUARDANDO_HUMANO_SEM_SOLUCAO`
- [ ] Nó Evolution API: Responder cliente (se for o caso)

### 4.4 Fluxo Condicional — Cenários
- [ ] **Cenário A** (IA resolve): Responder cliente + marcar RESOLVIDO
- [ ] **Cenário B** (IA achou solução mas precisa de humano): Status `AGUARDANDO_HUMANO_COM_SOLUCAO`, anexar solução
- [ ] **Cenário C** (IA não achou solução): Status `AGUARDANDO_HUMANO_SEM_SOLUCAO`, relatório técnico

### 4.5 Configuração de RAG no n8n
- [ ] Conector Qdrant no n8n (coleção `emsoft-knowledge-base`)
- [ ] Pipeline de ingestão: webhook de upload → chunking → embedding → inserir no Qdrant
- [ ] Estratégia de chunking: 500 tokens com overlap de 50 (para manuais ERP)
- [ ] Metadata: categoria, título, data

---

## Fase 5 — Integração LLM (IA Generativa)

### 5.1 Módulo app/ai/
- [ ] Serviço `OpenAIService`: wrapper para chat completion + embedding
- [ ] Serviço `OllamaService`: fallback local
- [ ] Serviço `AICache`: cache de respostas via Redis (evita reprocessar mensagens iguais)
- [ ] Fallback automático: tenta OpenAI, se falhar usa Ollama

### 5.2 Endpoints Auxiliares
- [ ] `POST /ai/sumarizar` — sumariza conversa de um chat
- [ ] `POST /ai/diagnosticar` — gera diagnóstico completo
- [ ] `POST /ai/classificar` — classifica apenas o problema

### 5.3 Sistema de Prompts
- [ ] Template para classificação de problema (qual módulo ERP)
- [ ] Template para sumarização de conversa
- [ ] Template para geração de solução (com contexto RAG)
- [ ] Template para diagnóstico técnico

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

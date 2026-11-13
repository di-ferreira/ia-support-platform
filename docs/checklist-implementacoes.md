# Checklist de Implementações

Gerado em 2026-11-09 a partir dos Registros de Gaps das specs (`docs/specs/00`–`14`); a fonte da verdade segue sendo cada spec.

- **166 entregues** `[x]` — gaps CORRIGIDO
- **35 pendentes** `[ ]` — gaps ABERTO (parciais marcados)
- Total: 201 itens

## Fases do plano (SPEC 13)

- [x] Fase 0 — Auditoria e baseline
- [x] Fase 1 — Departamentos e migração
- [x] Fase 2 — Classificação e roteamento (resta a auditoria 10-12; rota 03-19 fechada)
- [x] Fase 3 — Diagnóstico e ciclo de resolução
- [ ] Fase 4 — Frontend operacional (telas de departamento, filtros, painéis)
- [ ] Fase 5 — Integração Emsoft em modo mock (scaffold do contrato e outbox/worker feitos; falta artefato real de contrato)
- [ ] Fase 6 — Homologação externa (bloqueada pelo artefato de contrato, 11-1)
- [ ] Fase 7 — Rollout (bloqueado pela homologação)

## SPEC 00 — Escopo do Produto

- [x] **00-1** — Cenário A/B/C existiam só como prosa; nenhum nó decidia o cenário (Média)
- [x] **00-2** — RAG inalcançável: `/ai/solucionar` não era chamado pelo fluxo (**Crítica**)
- [x] **00-3** — Workflow n8n de 8 nós sem RAG/roteamento (**Alta**)
- [x] **00-4** — Docs citavam Supabase Storage como armazenamento (Baixa)
- [ ] **00-5** — Docs citavam stack NestJS/TypeScript/Prisma (Baixa)
- [ ] **00-6** — Docs citavam workflow de 19 nós (Baixa)
- [x] **00-7** — Backup cobre só Postgres/Supabase; MinIO órfão e backup do Qdrant nunca dispara em prod (**Alta**)
- [x] **00-8** — Status do chat nunca saía de `NOVO` no fluxo real (**Crítica**)
- [x] **00-9** — `ia_diagnosticos` nunca era populado (**Crítica**)
- [x] **00-10** — `tempo_medio_resposta` mede intervalo entre mensagens do mesmo atendente, não o tempo de primeira resposta (**Alta**)
- [ ] **00-11** — Sem CSAT/NPS nem coleta de feedback (Média)
- [ ] **00-12** — Mídia no WhatsApp: backend e workflow extraem `extendedText`/caption, mas a mídia não é armazenada e formatos não-texto caem em vazio (**Alta**)
- [x] **00-13** — Departamentos, roteamento e pedido explícito por humano/setor não existem (**Alta**)
- [ ] **00-14** — Integração com a API interna de chamados Emsoft não existe (**Alta**) *(parcial)*
- [ ] **00-15** — Sem outbox/idempotência para chamados externos (**Alta**)
- [x] **00-16** — Indicadores de sucesso por departamento/duplicidade sem instrumentação (Média)

## SPEC 01 — Domínio, Glossário e Máquina de Estados

- [ ] **01-1** — `.ai/` mantém docs com vocabulário/estados divergentes (`EM_ATENDIMENTO_HUMANO`, stack antiga) (Baixa)
- [x] **01-2** — `PATCH /webhooks/chat/status` **não** valida `STATUS_TRANSITIONS` — atualiza direto, inclusive saindo de `ENCERRADO` (**Alta**)
- [ ] **01-3** — Urgência da IA (`critica`) não tem coluna; existe só no prompt (Média)
- [x] **01-4** — Cenário A não alcança `RESOLVIDO` pela IA: `resolvido_pela_ia` leva a `AGUARDANDO_CLIENTE` e ninguém confirma (**Alta**)
- [ ] **01-5** — `chats.loja_id` nunca é populado; nenhum endpoint define a loja (Média)
- [x] **01-6** — `transferir` usa literais de string; `transferir_grupo` usa o enum (Baixa)
- [x] **01-7** — `chat["status"] == StatusChat.em_atendimento` compara string com membro de `StrEnum` (Baixa)
- [x] **01-8** — Sem tabela de auditoria; não há como saber quem mudou status/atribuição (Média)
- [x] **01-9** — Sem entidade departamento nem atribuição por departamento na máquina de estados (**Alta**)
- [x] **01-10** — Domínio não separa categoria ERP de departamento; intenção não é modelada (**Alta**)
- [x] **01-11** — Sem distinção de reabertura/confirmação de resolução pelo cliente além de `RESOLVIDO → IA_ANALISANDO` (Média)

## SPEC 02 — Modelo de Dados (Appwrite)

- [x] **02-1** — `CLASSIFY_SYSTEM` reconhece 7 categorias (`multiempresa`, `outro`); `CATEGORIA_CONHECIMENTO` tem 5 — artigos dessas áreas não podem ser gravados (**Alta**)
- [x] **02-2** — `CategoriaConhecimento` sem `multiempresa`, que é área real do negócio (Média)
- [ ] **02-3** — `TipoMensagem` sem `sticker`/`local`; o normalizador do webhook mapeia sticker→imagem, mas o enum não espelha a Evolution (Média)
- [x] **02-4** — `atendentes.setor` e `chats.setor_alvo` são string livre, sem enum/validação (legado a migrar para departamento) (Média)
- [ ] **02-5** — `chats.loja_id` nunca é populado (Média)
- [ ] **02-6** — `url_arquivo` existe em `mensagens`/`knowledge_bases`, sem upload/download/storage (Média)
- [x] **02-7** — `ia_diagnosticos` nunca era populado; `get_by_chat` sem chamador (**Crítica**)
- [x] **02-8** — CRUD da base de conhecimento não sincronizava o Qdrant (**Alta**)
- [ ] **02-9** — `tags` e `chat_tags` órfãs (sem repositório/rota/serviço) (Baixa)
- [x] **02-10** — Bootstrap aditivo **não propaga mudança de enum**; health degradado não implementado (**Alta**)
- [x] **02-11** — `backend/alembic/`, `app/models/*.py` (ORM) e `scripts/migrate.sh` apontam para PostgreSQL, que não é a fonte atual (**Alta**) — removido (2026-11-13): ORM e Alembic eliminados, `app/models/` ficou em reexports de `app.models.enums`
- [x] **02-12** — Sem índice único: unicidade de `email`/`documento` é check-then-insert, vulnerável a corrida (Média)
- [x] **02-13** — `scripts/seed_knowledge_base.py` importava `async_session` inexistente (**Alta**)
- [x] **02-14** — `scripts/seed_qdrant.py` lê do PostgreSQL e usa id inteiro como ponto Qdrant (**Alta**)
- [x] **02-15** — `dashboard_service.py` chama `clientes.get` dentro do loop de recentes (Média)
- [ ] **02-16** — Sem foreign key: `chats.cliente_id` pode apontar para cliente inexistente (Média)
- [x] **02-17** — Coleções `departamentos`, `regras_roteamento`, `integracao_chamados` e `integration_outbox` inexistentes (**Alta**)
- [x] **02-18** — `departamento_id` ausente em `atendentes`/`chats` (**Alta**)
- [x] **02-19** — `ia_diagnosticos` não guarda intenção, categoria ERP, departamento destino, artigos consultados nem razão (**Alta**)
- [x] **02-20** — Sem trilha de auditoria de atribuição/transferência (exigida em 04) (Média)

## SPEC 03 — Contrato da API FastAPI

- [x] **03-1** — `GET /dashboard` não aplica filtro de visibilidade (**Alta**)
- [x] **03-2** — `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse (**Alta**)
- [x] **03-3** — `PATCH /webhooks/chat/status` ignora `STATUS_TRANSITIONS` (**Alta**)
- [x] **03-4** — `/ai/*` usa query parameter para conteúdo do cliente (PII em access log) (**Alta**)
- [x] **03-5** — `/ai/solucionar` escrevia no chat furando a máquina de estados (**Alta**)
- [x] **03-6** — JWT do WebSocket viajava em query string (**Alta**)
- [ ] **03-7** — 502 devolve `str(e)` do `httpx`, expondo URL/corpo da Evolution (Média)
- [x] **03-8** — Rotas que alteram chat não emitem evento WebSocket (`status`, `pegar`, `transferir`, `assinar`, `prioridade`, kanban `mover`) (Média)
- [x] **03-9** — `POST /chats/{id}/assinar` existe (admin/supervisor) sem chamador no frontend (Baixa)
- [x] **03-10** — `/auth/refresh` e `PATCH /auth/password` existem e não são chamados pelo frontend (**Alta**)
- [ ] **03-11** — `POST /chats/enviar-whatsapp` tem lógica de negócio dentro da rota (Média)
- [ ] **03-12** — `GET /atendentes/ativos` tem a lógica dentro da rota (Baixa)
- [ ] **03-13** — `EvolutionService.criar_instancia` engole 403 e devolve resposta fabricada sem QR (Média)
- [x] **03-14** — Webhook padrão da Evolution aponta para URL hardcoded `/webhook/emsoft-whatsapp` (**Alta**)
- [ ] **03-15** — Nome da instância `"emsoft-support"` hardcoded em mensagens/evolution (Média)
- [x] **03-16** — `WEBHOOK_SECRET` sem validação no startup (Média)
- [ ] **03-17** — `GET /settings/ia-name` é público e não requer autenticação (Baixa)
- [ ] **03-18** — `/webhooks/chat/diagnostico` sem chamador (`/contexto` já é chamado pelo n8n) (Média)
- [x] **03-19** — Endpoints-alvo inexistentes: `/departamentos*`, `/chats/{id}/transferir-departamento`, `/atribuir-atendente`, `/roteamento`, `/ai/classificar-intencao`, `/integracoes/chamados/*` (**Alta**)

## SPEC 04 — Matriz de Permissões (RBAC)

- [x] **04-1** — `GET /dashboard` não aplica filtro de visibilidade; atendente lê KPIs globais e nomes de clientes (**Alta**)
- [x] **04-2** — `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse (**Alta**)
- [x] **04-3** — Frontend oculta ações por perfil e não tem guarda de rota; digitando a URL alcança `/usuarios` e `/configuracoes` (Média)
- [x] **04-4** — Regra "supervisor só cria `atendente`" está no serviço e sem teste (**Alta**)
- [x] **04-5** — Regra "só admin altera `perfil`" está no serviço e sem teste (**Alta**)
- [x] **04-6** — `ChatService` cobre transições, mas `pegar`/`transferir`/`transferir_grupo`/`assinar`/`definir_prioridade`/`listar` (filtro) seguem sem teste (**Alta**)
- [x] **04-7** — `WEBHOOK_SECRET` ainda força status de qualquer chat (pulando a máquina de estados) e cria diagnóstico; mitigado por fail-closed e rate limit (**Alta**)
- [ ] **04-8** — `EvolutionService.criar_instancia` engole 403 e devolve sucesso sem QR (Média)
- [ ] **04-9** — `GET /atendentes/ativos` retorna id/nome/perfil/setor de todos os ativos para qualquer autenticado (Baixa)
- [x] **04-10** — Escopo por departamento não é aplicado (departamento não existe) (**Alta**)
- [x] **04-11** — Identidade de serviço da IA / `actor_type` auditável não implementada (Média)
- [x] **04-12** — Sem auditoria de atribuição/transferência (ator, motivo, antes/depois) (Média)
- [x] **04-13** — chat ENCERRADO podia ser assumido/atribuído (`pegar`/`assinar`/`atribuir_atendente`) (Média)

## SPEC 05 — Pipeline de IA, Classificação, RAG e Decisão

- [x] **05-1** — Pipeline de IA não conectado ao fluxo produtivo do n8n (**Crítica**)
- [x] **05-2** — `/webhooks/chat/diagnostico` sem chamador; `ia_diagnosticos` não populado (**Crítica**)
- [x] **05-3** — `PATCH /webhooks/chat/status` sem chamador; status nunca saía de `NOVO` (**Crítica**)
- [x] **05-4** — Cenário A não tem caminho de fechamento: vai a `AGUARDANDO_CLIENTE` e ninguém confirma (**Alta**)
- [x] **05-5** — CRUD da base de conhecimento não sincronizava o Qdrant (**Alta**)
- [x] **05-6** — Falha de RAG degradava para "nenhum artigo" (Cenário C falso) (**Alta**)
- [x] **05-7** — `/ai/solucionar` furava a máquina de estados; `except: pass` engolia falha (**Alta**)
- [x] **05-8** — Resultado da LLM sem validação de shape (Média)
- [x] **05-9** — `/ai/*` sem resposta Pydantic: `/ai/solucionar` tem `WebhookSolucaoResponse`; `classificar`/`analisar` devolvem dict cru (Média)
- [x] **05-10** — `/ai/classificar` e `/ai/analisar` usam query param (conteúdo do cliente na URL) (**Alta**)
- [x] **05-11** — `VECTOR_SIZE=768` incompatível com `text-embedding-3-small` (1536) (**Alta**)
- [x] **05-12** — `get_llm` caía em Ollama silenciosamente se `LLM_PROVIDER=openai` sem chave (Média)
- [x] **05-13** — `except: pass` engolia falha de embedding (Média)
- [ ] **05-14** — Drift de modelo: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` (Média)
- [ ] **05-15** — `AICache` engole toda exceção em `get`/`set`/`clear`; `clear()` nunca é chamado (Média)
- [x] **05-16** — `prompt.format` quebrava com `{`/`}` de artigo (**Alta**)
- [x] **05-17** — Categoria `multiempresa` reconhecida pela IA mas ausente do schema (**Alta**)
- [x] **05-18** — `IADiagnosticoRepository.get_by_chat` sem chamador (Baixa)
- [ ] **05-19** — Dependência `openai` declarada e nunca importada (clients usam `httpx`) (Baixa)
- [x] **05-20** — Sem teste unitário direto de `ai/router.py`, `ai_cache.py` e clients; pipeline coberto por `test_ai_pipeline.py` (**Alta**)
- [x] **05-21** — Classificação de intenção não separa categoria ERP de departamento; `CLASSIFY_SYSTEM` só devolve categoria (**Alta**)
- [x] **05-22** — Resolução determinística de regras de roteamento inexistente (**Alta**)
- [x] **05-23** — Diagnóstico não persiste intenção/departamento/artigos consultados/razão (**Alta**)
- [x] **05-24** — Sem dataset rotulado nem regressão de intenção/roteamento (Média)

## SPEC 06 — Workflow n8n e Transporte WhatsApp

- [x] **06-1** — Path do webhook divergente entre workflow e Evolution (**Alta**)
- [x] **06-2** — `RESOLVIDO → IA_ANALISANDO` ausente da máquina de estados (**Alta**)
- [x] **06-3** — Sem deduplicação; reconexão persistia a mensagem duas vezes (**Alta**)
- [x] **06-4** — URL do backend hardcoded no workflow (**Crítica**)
- [x] **06-5** — `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` ausente de compose/.env (**Crítica**)
- [x] **06-6** — Nome da instância hardcoded no nó (Média)
- [x] **06-7** — Só `message.conversation` era lido (**Alta**)
- [x] **06-8** — AI Agent sem tools alucinava (**Crítica**)
- [x] **06-9** — `N8N_ENCRYPTION_KEY`/`N8N_SECURE_COOKIE` ausentes (Média)
- [x] **06-10** — Nenhum nó com `onError` (**Alta**)
- [x] **06-11** — `docs/n8n-workflow.md` desatualizado (12 nós/RAG no n8n) (Média)
- [x] **06-12** — Doc descrevia chunking 500/50 com embedding OpenAI (Média)
- [x] **06-13** — Workflow `active: false` no arquivo versionado (Baixa)
- [x] **06-14** — `pinData` do webhook com `fromMe: true` (Baixa)
- [x] **06-15** — `extra_hosts: host.docker.internal` ausente (Média)
- [x] **06-16** — `remoteJid` cru usado em pontos sensíveis (Média)
- [ ] **06-17** — Mídia não é preservada (URL/arquivo): apenas caption é extraída (**Alta**)
- [ ] **06-18** — `onError: continue` silencia falhas sem retry/registro estruturado (Média)

## SPEC 07 — Frontend (Painel de Atendimento)

- [x] **07-1** — Token JWT do WebSocket na query string (**Alta**)
- [x] **07-2** — Sem refresh token/renovação; sessão cai após 60 min (**Alta**)
- [x] **07-3** — WebSocket sem reconexão nem backoff (Média)
- [x] **07-4** — Cores raw do Tailwind (`green/red/blue/gray`) fora dos tokens `@theme` (Média)
- [x] **07-5** — `chat-store` (`chatAtivo`) não é usado; estado local duplica a fonte (Baixa)
- [x] **07-6** — Selects de status/prioridade usam `<select>` nativo (Baixa)
- [x] **07-7** — Manifest referenciava `relatorios.html` fora de escopo (Média)
- [x] **07-8** — Manifest referenciava `ia-dashboard.html` fora de escopo (Média)
- [x] **07-9** — Sem telas de departamento, fila por departamento e transferência por departamento (**Alta**)
- [x] **07-10** — Sem painel de diagnóstico de intenção/roteamento nem status de sincronização do chamado (**Alta**)
- [x] **07-11** — Sem guarda de rota por perfil (Média)

## SPEC 08 — Requisitos Não Funcionais, Segurança e Observabilidade

- [x] **08-1** — `CORS_ORIGINS` default só `localhost:3000` (**Alta**)
- [x] **08-2** — Comportamento de `verify_webhook` sem segredo não fixado (**Alta**)
- [x] **08-3** — `/health` não checa dependências; sem readiness (Média)
- [x] **08-4** — Sem rate limiting em login/webhooks (**Alta**)
- [x] **08-5** — Sem logging estruturado nem request-id/correlação (Média)
- [ ] **08-6** — Sem métricas/tracing/APM; nenhum SLO observável (Média) *(parcial)*
- [x] **08-7** — `DATABASE_URL` default com credenciais em claro (Baixa) — removido (2026-11-13): `database_url`/`database_url_prod` saíram do `Settings` e do compose de produção
- [x] **08-8** — WebSocket aceitava token por query string (**Alta**)
- [x] **08-9** — Métricas de produto (resolução confirmada, transbordo, roteamento, duplicidade) sem instrumentação; `tempo_medio_resposta` com semântica errada (**Alta**)
- [ ] **08-10** — Degradação da integração Emsoft/outbox não implementada (outbox não existe) (**Alta**) *(parcial)*
- [ ] **08-11** — Timeout/retry/backoff explícitos de integrações externas não implementados (**Alta**)
- [x] **08-12** — Health check degradado do bootstrap não implementado (Média) (coberto por 08-3)

## SPEC 09 — Infraestrutura, Configuração e Deploy

- [x] **09-1** — Appwrite (store primária) ausente da pilha prod; backend aponta para `127.0.0.1:8020` (**Crítica**)
- [x] **09-2** — Bloco de env do backend prod incompleto (`SECRET_KEY`, `APPWRITE_*`, `WEBHOOK_SECRET`, `QDRANT_URL`, `OLLAMA_*`, `CORS_ORIGINS`) (**Crítica**)
- [x] **09-3** — MinIO órfão no compose prod sem referência no código (Baixa)
- [x] **09-4** — Pilha do Appwrite em rede isolada; backend prod não a alcança (**Alta**)
- [x] **09-5** — Backup Qdrant usa bind mount divergente do volume named de prod (**Alta**)
- [x] **09-6** — Sem backup de Appwrite/n8n/evolution-db; bloco Supabase remanescente (**Alta**)
- [x] **09-7** — `backup.sh` não é agendado (**Alta**)
- [x] **09-8** — Senha do Postgres em claro no compose/string da Evolution (Média)
- [x] **09-9** — Drift Python: pyproject/ruff/mypy/CI em 3.11 vs `Dockerfile` `3.12-slim` (Baixa)
- [ ] **09-10** — Drift de modelo Ollama: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` (Média)
- [x] **09-11** — `infra/.env.prod` não era gitignored (**Alta**)
- [x] **09-12** — Alembic/Postgres híbrido com runtime em Appwrite (Média) — removido (2026-11-13): caminho morto Alembic/ORM/Postgres eliminado do backend
- [x] **09-13** — Env do n8n (`BACKEND_URL`/`EVOLUTION_INSTANCE`/`N8N_BLOCK_ENV_ACCESS_IN_NODE`) ausente de compose/.env (**Alta**)
- [x] **09-14** — CI: mypy e lint do frontend report-only; sem job de teste do frontend (Média)
- [x] **09-15** — Sem serviço de LLM (Ollama) na pilha prod nem `OLLAMA_URL` (**Crítica**)
- [x] **09-16** — `start-prod.sh`: `sleep 5` em vez de aguardar healthcheck; roda Alembic (Baixa)
- [ ] **09-17** — Sem variáveis `EMSOFT_CHAMADOS_*` nem serviço de worker de integração (**Alta**) *(parcial)*
- [ ] **09-18** — Sem runbook de rollout/rollback da integração Emsoft (Média)

## SPEC 10 — Departamentos, Classificação de Intenção e Roteamento

- [x] **10-1** — Coleção `departamentos` inexistente (**Alta**)
- [x] **10-2** — Coleção `regras_roteamento` inexistente (**Alta**)
- [x] **10-3** — `atendentes.departamento_id` ausente; `setor` legado é string livre (**Alta**)
- [x] **10-4** — `chats.departamento_id` ausente; `setor_alvo` legado é string livre (**Alta**)
- [x] **10-5** — Endpoints de CRUD `/departamentos*` inexistentes (**Alta**)
- [x] **10-6** — `/chats/{id}/transferir-departamento` e `/chats/{id}/atribuir-atendente` inexistentes (existe `transferir-grupo` por `setor` livre) (**Alta**)
- [x] **10-7** — `/chats/{id}/roteamento` (resolver determinístico) inexistente (**Alta**)
- [x] **10-8** — `/ai/classificar-intencao` inexistente; classifier só devolve categoria ERP (**Alta**)
- [x] **10-9** — Seed idempotente de departamentos inexistente (Média)
- [x] **10-10** — Migração de `setor`/`setor_alvo` para `departamento_id` inexistente (**Alta**)
- [x] **10-11** — `pegar`/`transferir` não validam departamento/atividade do atendente (**Alta**)
- [x] **10-12** — Sem auditoria de transferência/atribuição (Média)

## SPEC 11 — Integração com a API Interna de Chamados Emsoft

- [ ] **11-1** — Gate de contrato: Swagger/OpenAPI, Postman ou exemplos reais da API de chamados **não obtidos** (probe 2026-11-09: endpoint vivo, envelope 401, sem Swagger público; re-probe 2026-11-10: endpoint vivo, sem Swagger público, cadeia de certificado TLS incompleta — ver [pedido de contrato](pedido-contrato-api-emsoft.md)) (**Bloqueante**) *(parcial)*
- [x] **11-2** — Adapter/client `app/integrations/emsoft_chamados/` inexistente (**Alta**)
- [x] **11-3** — Coleção `integracao_chamados` inexistente (**Alta**)
- [x] **11-4** — Config `EMSOFT_CHAMADOS_*` inexistente (**Alta**)
- [x] **11-5** — Identidade IA (`EMSOFT_CHAMADOS_AI_USER_ID`) e mapeamento de atendentes/departamentos ausente (**Alta**)
- [x] **11-6** — Endpoints `/integracoes/chamados/*` (consulta/reprocessamento) inexistentes (**Alta**)
- [x] **11-7** — Reconciliação de timeout ambíguo e idempotência externa inexistentes (**Alta**)

## SPEC 12 — Confiabilidade, Outbox, Idempotência e Reprocessamento

- [x] **12-1** — Coleção `integration_outbox` inexistente (**Alta**)
- [x] **12-2** — Worker/lock/lease de outbox inexistente (**Alta**)
- [x] **12-3** — `event_key` determinística/idempotency key inexistente (**Alta**)
- [x] **12-4** — Timeout/retry/backoff+jitter de integrações externas inexistentes (**Alta**)
- [x] **12-5** — Reconciliação de timeout ambíguo inexistente (**Alta**)
- [x] **12-6** — Logs sem correlation/event key (Média)
- [x] **12-7** — Sem painel de pendência/reprocessamento para operador (Média)
- [x] **12-8** — Evento obsoleto do outbox não é descartado (`event_version` só entra na `event_key`); versão antiga pode sobrescrever o estado no sistema externo com dado velho (**Alta**)

## SPEC 14 — Estratégia de testes

- [x] **14-1** — `AIPipelineService` é coberto, mas `ai/router.py`, `ai_cache.py`, `ollama_service.py` e `openai_service.py` não têm teste unitário direto (**Alta**)
- [x] **14-2** — Stub de LLM/embedder via monkeypatch de `get_llm`/`get_embedder` permite exercitar RAG → cenário de forma determinística (**Crítica**)
- [x] **14-3** — `qdrant_service.py` sem teste unitário: `search_similar`/`upsert`/`ensure_collection`, dimensão 768, `article_point_id` (**Alta**)
- [x] **14-4** — Render de prompt com conteúdo dinâmico não quebra mais (constantes + f-string) e o veredito é validado por Pydantic (**Alta**)
- [x] **14-5** — Webhook de mensagem coberto ponta a ponta: payload bruto Evolution, tipos/caption e dedup por `whatsapp_message_id` (**Alta**)
- [x] **14-6** — Frontend sem infraestrutura de teste (sem `test` script, sem Vitest/Playwright) (**Alta**) *(Vitest + jsdom + Testing Library; E2E Playwright `login-inbox.spec.ts` roda o fluxo login→inbox contra a stack)*
- [x] **14-7** — n8n sem harness de teste; JSON ativo sem validação automatizada de nós/env (Média)
- [x] **14-8** — Sem testes de integração reais (Appwrite/Qdrant/Evolution/Emsoft); tudo em fakes (Média) *(suíte `backend/tests/integracao` com 7 testes `pytest.mark.integracao` + job noturno `integracao` no CI com services Qdrant/Redis; Appwrite/Evolution/Emsoft pulam sem credenciais)*
- [x] **14-9** — CI sem threshold de cobertura; mypy e lint frontend report-only — regressões em IA não bloqueiam merge (Média)
- [x] **14-10** — Sem teste que garanta a dimensão de embedding (768 vs 1536); o bloqueio OpenAI (ADR-0005) não é travado por teste (**Alta**)
- [x] **14-11** — Sem testes de classificação de intenção, separação categoria ERP × departamento e resolução de roteamento (**Alta**)
- [x] **14-12** — Sem contract tests do adapter Emsoft e do ciclo outbox/reprocessamento (**Alta**)

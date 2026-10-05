# EMSoft Support AI — TODO List

> **⚠️ Histórico de implementação.** Este arquivo registra as fases na ordem em que
> foram executadas. **Não é mais a fonte de verdade nem o índice de trabalho.**
>
> - **Especificações + registro de gaps (fonte de verdade):**
>   [`docs/specs/`](docs/specs/) — cada spec termina com um *Registro de Gaps*; um gap
>   `ABERTO` é o trabalho Known.
> - **O que mudou depois desta lista:**
>   - A fonte de dados é **Appwrite** (não PostgreSQL/Supabase).
>   - O **backend é dono da IA** — RAG + LLM + decisão do cenário A/B/C
>     ([ADR-0004](docs/specs/adr/0004-backend-dono-da-ia.md)); o n8n é só transporte.
>   - O **alvo de LLM/embedding é Ollama** (768); o OpenAI está bloqueado para RAG
>     ([ADR-0005](docs/specs/adr/0005-dimensao-de-embedding.md)).
> - **Atualização (2026-10-05):** o pipeline RAG foi validado em runtime e o workflow n8n
>   foi reescrito como orquestrador de transporte, sem decisão de IA e sem chamada de Ollama.
>   O estado atual segue nos [Registros de Gaps](docs/specs/).

---

## Status Geral (histórico)

| Fase | Descrição | Status histórico |
|------|-----------|--------|
| 1 | Infraestrutura (Evolution, n8n, Qdrant) | ✅ |
| 2 | Evolution Integration Service | ✅ |
| 3 | WhatsApp Reply (atendente → cliente) | ✅ |
| 4 | WebSocket Tempo Real | ✅ |
| 5 | Página de Configuração WhatsApp | ✅ |
| 6 | Base de Conhecimento (PostgreSQL) | ✅ |
| 7 | Qdrant + RAG Semântico | ✅ |
| 8 | Workflow n8n Completo | ✅ |
| 9 | Gerenciamento de Usuários | ✅ |

---

## Atualização (2026-10-05)

- [x] Seed idempotente da base de conhecimento no Appwrite e no Qdrant (20 artigos, 20 pontos, dimensão 768)
- [x] Validação runtime do pipeline RAG no backend: `POST /webhooks/mensagem`, `GET /webhooks/chat/{chat_id}/contexto` e `POST /webhooks/ai/solucionar`
- [x] Persistência do diagnóstico IA e espelho de status/solução/confiança em Appwrite confirmada
- [x] Workflow n8n reescrito como orquestrador de transporte, sem decisão de IA e sem chamada de Ollama
- [x] Infra e `.env.example` atualizados para expor ao n8n `WEBHOOK_SECRET`, `BACKEND_URL`, `EVOLUTION_INSTANCE` e `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- [ ] Importar/ativar o workflow atual no n8n e validar o caminho vivo Evolution → n8n → backend → WhatsApp
- [ ] Revisar os gaps de 00, 05, 06 e 09 após a validação do fluxo vivo

---

## Fase 1 — Infraestrutura ✅

- [x] Evolution API rodando (`:8080`)
- [x] n8n rodando (`:5678`)
- [x] Qdrant rodando (`:6333`)
- [x] Redis rodando (`:6379`)
- [x] Instância WhatsApp `emsoft-support` criada e conectada
- [x] Webhook Evolution → n8n configurado (evento `MESSAGES_UPSERT`)
- [x] Collection Qdrant `emsoft-knowledge-base` criada (size=768, Cosine)
- [x] Workflow n8n importado (`infra/n8n/workflow-support-ai.json`)
- [x] n8n acessa backend via `http://host.docker.internal:8001`

## Fase 2 — Backend Evolution Integration Service ✅

- [x] `app/services/evolution_service.py` — `EvolutionService`
  - `criar_instancia`, `obter_qrcode`, `obter_qrcode_base64`, `get_status`
  - `configurar_webhook`, `desconectar`, `deletar_instancia`, `enviar_texto`
- [x] `app/schemas/evolution.py` — schemas de request/response
- [x] `app/api/routes/evolution.py` — 7 endpoints REST (admin-only)
- [x] Router registrado no `main.py`

## Fase 3 — Resposta do Atendente via WhatsApp ✅

- [x] `POST /chats/{id}/mensagens` com `remetente=atendente` chama `EvolutionService.enviar_texto`
- [x] Mapeia `chat.whatsapp_number` para número de destino

## Fase 4 — Frontend Tempo Real ✅

- [x] `useChatSocket` hook — WebSocket raw (`/ws/chat/{id}`) com token JWT
- [x] Invalida React Query ao receber `nova_mensagem`, `status_update`, `diagnostico`
- [x] Polling reduzido para 30s (fallback)
- [x] Backend `ConnectionManager.send_event()` — push das rotas para WebSocket

## Fase 5 — Frontend Configuração WhatsApp ✅

- [x] Página `/configuracoes` — criar instância, QR code, webhook, desconectar
- [x] Indicador de status WhatsApp no Header (bolinha verde/vermelha)
- [x] Link "Configurações" na Sidebar (admin-only)

## Fase 6 — Base de Conhecimento ✅

- [x] CRUD `/knowledge-base` (backend + frontend)
- [x] `scripts/seed_knowledge_base.py` — 20 artigos em 5 categorias (fiscal, estoque, compras, vendas, financeiro)
- [x] Filtro por categoria + busca no frontend

## Fase 7 — Qdrant + RAG Semântico ✅

- [x] `app/services/qdrant_service.py` — `ensure_collection`, `search_similar`, `upsert_article`
- [x] `qdrant_url` adicionado ao Settings (default `http://localhost:6333`)
- [x] `scripts/seed_qdrant.py` — gera embeddings via Ollama (`nomic-embed-text`) e popula Qdrant
- [x] `POST /ai/solucionar` agora usa busca semântica via Qdrant em vez de `LIMIT 5` no PostgreSQL
- [x] Coleção `emsoft-knowledge-base` populada com 20 artigos indexados

## Fase 8 — Workflow n8n Completo ✅

> **Nota (2026-10-05):** a Fase 8 abaixo descreve o estado histórico. O workflow atual foi
> reescrito como orquestrador de transporte: `Webhook → If → Salvar mensagem → Contexto →
> Resolver IA → Enviar texto + Salvar resposta`.

- [x] Nó **Salvar mensagem do cliente** — HTTP Request `POST /webhooks/mensagem` (paralelo ao If)
- [x] Nó **Salvar resposta da IA** — HTTP Request `POST /webhooks/mensagem` (paralelo ao Enviar texto)
- [x] Fluxo: Webhook → If + Salvar msg → AI Agent → Enviar texto + Salvar resposta
- [x] `Enviar texto` com instanceName `emsoft-support` (corrigido)

---

## Fase 9 — Gerenciamento de Usuários ✅

- [x] `POST /auth/usuarios` — criar usuário (admin/supervisor)
- [x] `GET /auth/usuarios` — listar usuários (admin/supervisor)
- [x] `PATCH /auth/usuarios/{id}` — atualizar (admin: tudo; supervisor: só atendentes)
- [x] `DELETE /auth/usuarios/{id}` — desativar (admin only)
- [x] Supervisor cria apenas perfil `atendente`; Admin pode todos os perfis
- [x] Frontend `/usuarios` — tabela + modal criar/editar
- [x] Sidebar: link Usuários visível para admin e supervisor

## Fase 10 — Kanban + Fluxo Completo de Atendimento ✅

- [x] Migration: `setor` em `Atendente`, `setor_alvo` em `Chat`
- [x] `PATCH /chats/{id}/pegar` — auto-atribuição (qualquer atendente)
- [x] `PATCH /chats/{id}/transferir` — transferir para outro atendente
- [x] `PATCH /chats/{id}/transferir-grupo` — transferir para grupo/setor
- [x] `GET /atendentes/ativos` — listar atendentes disponíveis
- [x] Visibilidade: atendentes veem chats não-atribuídos + do seu setor
- [x] Kanban: botão "Pegar" + "Transferir" + badge de setor
- [x] Atendimento: botão "Pegar" na inbox + "Transferir" no header
- [x] Modal de transferência (aba atendente + aba grupo)

## Próximas Melhorias (backlog)

### WebSocket — Reconexão Automática
- [ ] Reconexão com exponential backoff em `useChatSocket`
- [ ] Renovar token JWT expirado antes de reconectar
- [ ] Verificar se todas as rotas que alteram chat chamam `send_event()`

### Dashboard
- [ ] Métricas de tempo médio de resposta
- [ ] Indicador de satisfação / NPS

### Testes
- [ ] Testes para EvolutionService
- [ ] Testes para WebhookService
- [ ] Testes para ConnectionManager (WebSocket)
- [ ] Testes de integração fluxo completo

### Melhorias Gerais
- [ ] Componentes Radix UI (instalados mas não utilizados)
- [ ] PWA / notificações push no navegador
- [ ] Upload de mídia (já tem campo `url_arquivo` no model)
- [ ] Editar/deletar mensagens

---

## Fluxo Final

```
Cliente WhatsApp
  → Evolution API (:8080) recebe mensagem
    → Webhook → n8n (:5678)
      → If (fromMe == false)
        → Salvar mensagem (POST /webhooks/mensagem)
        → Contexto (GET /webhooks/chat/{chat_id}/contexto)
          → Resolver IA (POST /webhooks/ai/solucionar)
            → Enviar texto (Evolution API → WhatsApp cliente)
            → Salvar resposta IA (POST /webhooks/mensagem)
              → WebSocket → Frontend em tempo real

Atendente responde pelo Frontend
  → POST /chats/{id}/mensagens (remetente=atendente)
    → Salvar no banco
    → EvolutionService.enviar_texto → WhatsApp cliente
    → WebSocket broadcast → Frontend em tempo real
```

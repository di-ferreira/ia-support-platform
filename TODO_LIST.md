# EMSoft Support AI — TODO List

## Status Geral

| Fase | Descrição | Status |
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
      → Salvar mensagem (HTTP POST /webhooks/mensagem)
      → If (fromMe == false)
        → AI Agent (Ollama + RAG Qdrant)
          → Enviar texto (Evolution API → WhatsApp cliente)
          → Salvar resposta IA (HTTP POST /webhooks/mensagem)
            → WebSocket → Frontend em tempo real

Atendente responde pelo Frontend
  → POST /chats/{id}/mensagens (remetente=atendente)
    → Salvar no banco
    → EvolutionService.enviar_texto → WhatsApp cliente
    → WebSocket broadcast → Frontend em tempo real
```

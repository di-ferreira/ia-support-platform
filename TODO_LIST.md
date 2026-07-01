# EMSoft Support AI — TODO List

## Integração WhatsApp (faltante)

### Diagnóstico

**Já existe:**
- Evolution API rodando (`:8080`), n8n rodando (`:5678`)
- Workflow n8n definido (`infra/n8n/workflow-support-ai.json`)
- Backend com webhooks (mensagem, status, diagnóstico, contexto) — sem auth, para n8n
- Chat state machine (7 status), AI endpoints (classify, analyze, solve + RAG)
- WebSocket (`/ws/chat/{id}`)
- Frontend com atendimento, kanban, dashboard, CRM
- `evolution_api_url` e `evolution_api_key` no config (mas **não implementado**)

**Falta:**
- Service de integração Evolution API no backend (enviar mensagem, gerenciar instância)
- Criar instância na Evolution API + escanear QR code
- Configurar webhook da Evolution → n8n
- Importar workflow no n8n + configurar credenciais
- Endpoint para atendente responder via WhatsApp
- WebSocket real-time no frontend (substituir polling)
- Página de configuração da instância WhatsApp
- Indicador visual de status do WhatsApp (conectado/desconectado)
- Qdrant collection + base de conhecimento populada

---

### Passo a Passo

#### Fase 1 — Infra (setup manual, ~10 min)

- [ ] **1.1** Importar workflow no n8n
      ```
      Acessar http://localhost:5678
      Workflows → Add Workflow → Import from File
      Selecionar infra/n8n/workflow-support-ai.json
      ```
- [ ] **1.2** Configurar credenciais no n8n
      - HTTP Header Auth: `EMSoft API Token` com um JWT válido do admin
      - OpenAI (se usar): API Key
      - Qdrant: URL `http://qdrant:6333`
- [ ] **1.3** Adicionar env vars no n8n (Settings → Environment Variables)
      ```
      API_URL=http://backend:8001
      API_TOKEN=<jwt-do-admin>
      EVOLUTION_API_URL=http://evolution-api:8080
      EVOLUTION_INSTANCE=emsoft-support
      QDRANT_URL=http://qdrant:6333
      ```
- [ ] **1.4** Criar instância na Evolution API
      ```bash
      curl -X POST http://localhost:8080/instance/create \
        -H "Content-Type: application/json" \
        -H "apiKey: evolution_dev_key" \
        -d '{"instanceName": "emsoft-support"}'
      ```
- [ ] **1.5** Obter QR code e escanear no WhatsApp
      ```bash
      curl -X GET http://localhost:8080/instance/connect/emsoft-support \
        -H "apiKey: evolution_dev_key"
      # Acessar http://localhost:8080/instance/qrcode/emsoft-support no navegador
      ```
- [ ] **1.6** Configurar webhook da Evolution → n8n
      ```bash
      curl -X POST http://localhost:8080/webhook/set/emsoft-support \
        -H "Content-Type: application/json" \
        -H "apiKey: evolution_dev_key" \
        -d '{
          "webhookUrl": "http://n8n:5678/webhook/emsoft-whatsapp",
          "events": ["messages.upsert"]
        }'
      ```
- [x] **1.1** Importar workflow no n8n
      ```
      Acessar http://localhost:5678
      Workflows → Add Workflow → Import from File
      Selecionar infra/n8n/workflow-support-ai.json
      ```
- [x] **1.2** Configurar credenciais no n8n
- [x] **1.3** Adicionar env vars no n8n
- [x] **1.4** Criar instância na Evolution API
      (via página /configuracoes na plataforma — admin only)
- [x] **1.5** Obter QR code e escanear no WhatsApp
      (via página /configuracoes — imagem base64 inline)
- [x] **1.6** Configurar webhook da Evolution → n8n
      (via página /configuracoes — botão "Configurar Webhook")
- [x] **1.7** Criar collection Qdrant
      ```bash
      curl -X PUT http://localhost:6333/collections/emsoft-knowledge-base \
        -H "Content-Type: application/json" \
        -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
      ```

#### Fase 2 — Backend (Evolution Integration Service) ✅

- [x] **2.1** Criar `app/services/evolution_service.py`
      - Métodos: `criar_instancia`, `obter_qrcode`, `configurar_webhook`, `enviar_texto`, `get_status`
      - Usar `httpx.AsyncClient` para chamar Evolution API
      - Ler config `evolution_api_url` + `evolution_api_key`
- [x] **2.2** Criar `app/schemas/evolution.py`
      - Schemas: `InstanceCreate`, `InstanceResponse`, `QRCodeResponse`, `WebhookConfig`, `SendText`
- [x] **2.3** Criar `app/api/routes/evolution.py`
      - Endpoints:
        - `POST /evolution/instance` — criar instância
        - `GET /evolution/instance/qrcode` — obter QR code
        - `POST /evolution/instance/webhook` — configurar webhook
        - `GET /evolution/instance/status` — status da conexão
        - `POST /evolution/send-text` — enviar mensagem texto
- [x] **2.4** Registrar router no `main.py`

#### Fase 3 — Resposta do Atendente via WhatsApp ✅

- [x] **3.1** Alterar `POST /chats/{id}/mensagens` (app/api/routes/mensagens.py)
      - Quando `remetente=atendente`, após salvar a mensagem, chamar `EvolutionService.enviar_texto`
      - Mapear `chat.whatsapp_number` para o número de destino

#### Fase 4 — Frontend (Tempo Real) ✅

- [x] **4.1** WebSocket real-time via hook `useChatSocket`
      - Conecta WebSocket raw do backend (`/ws/chat/{id}`) com token JWT
      - Invalida queries do React Query ao receber eventos (`nova_mensagem`, `status_update`, `diagnostico`)
- [x] **4.2** Reduzir polling (`refetchInterval` de 10s/5s para 30s como fallback)
- [x] **4.3** Backend: `ConnectionManager.send_event()` para push de eventos das rotas
      - Webhooks (`mensagem`, `status`, `diagnostico`) agora broadcast via WS
      - Rota de mensagens do atendente também broadcast

#### Fase 5 — Frontend (Configuração WhatsApp) ✅

- [x] **5.1** Criar página `/configuracoes`
      - Botão "Criar Instância"
      - Exibir QR code (imagem)
      - Status da conexão (conectado/desconectado/escanear)
      - Botão "Desconectar"
      - Botão "Configurar Webhook" (aponta para n8n)
- [x] **5.2** Adicionar indicador de status no Header (bolinha verde/vermelha)
- [x] **5.3** Adicionar link "Configurações" na Sidebar (ícone Settings)

#### Fase 6 — Base de Conhecimento ✅

- [x] **6.1** Popular artigos na base de conhecimento via API
      - Criar artigos para categorias: fiscal, estoque, compras, vendas, financeiro
      - Mínimo 3-5 artigos por categoria para RAG funcionar
- [x] **6.2** Script `scripts/seed_knowledge_base.py` com 20+ artigos em lote
      - Executar: `python scripts/seed_knowledge_base.py` (idempotente)

---

### Fluxo Final (quando tudo estiver pronto)

```
Cliente WhatsApp
  → Evolution API (:8080) recebe mensagem
    → Webhook → n8n (:5678)
      → Backend (/webhooks/mensagem) salva
        → IA + RAG classifica/diagnostica
          → n8n decide cenário A/B/C
            ├─ A: Evolution → resposta ao cliente
            ├─ B: Kanban + Frontend (WebSocket)
            └─ C: Kanban + Frontend (WebSocket)
                  ↓
              Atendente responde
                → Backend (/chats/{id}/mensagens)
                  → Evolution API → WhatsApp do cliente
```

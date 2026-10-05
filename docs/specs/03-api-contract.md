# SPEC 03 — Contrato de API

Base: FastAPI. Prefixo global: nenhum (rotas na raiz). Documentação interativa em
`/docs` e `/redoc`.

## Autenticação

Dois mecanismos, para dois públicos distintos.

### Usuário humano — JWT Bearer

```http
Authorization: Bearer <access_token>
```

| Token | Validade | Claim `typ` | Uso |
|---|---|---|---|
| Access | `ACCESS_TOKEN_EXPIRE_MINUTES` (padrão 60) | `access` | Toda rota autenticada |
| Refresh | `REFRESH_TOKEN_EXPIRE_DAYS` (padrão 7) | `refresh` | Só em `POST /auth/refresh` |

Regras:

- O claim `typ` **tem** ser conferido. Um refresh usado como access é rejeitado com 401,
  e um access usado como refresh também.
- O perfil (`perfil`) vem do token, mas **nunca éIENotado**: o backend relê o usuário do
  Appwrite e usa o `perfil` de lá. Desativar a conta invalida o token imediatamente.
- Token expirado, assinatura inválida ou malformado → **401**.

### Máquina (n8n) — Segredo compartilhado

```http
X-Webhook-Secret: <WEBHOOK_SECRET>
```

Aplicado a todas as rotas sob `/webhooks/**`. Comparação por `hmac.compare_digest`
(tempo constante).

- Se `WEBHOOK_SECRET` não estiver definido, **todas** as rotas de webhook respondem
  **401**, mesmo em desenvolvimento. É fail-closed por desenho.
- O segredo é o mesmo para todos os chamadores. Não há identidade por chamador, nem
  timestamp, nem proteção contra replay.

> Ver [05-ai-pipeline](05-ai-pipeline.md) §Autenticação M2M para por que `/ai/*` não
> pode ser chamado pelo n8n hoje.

## Códigos de erro

| Código | Quando | Corpo |
|---|---|---|
| **400** | Transição de status inválida; `pegar` em chat já atribuído | `{"detail": "..."}` |
| **401** | Sem token; token expirado/inválido; `typ` errado; webhook sem segredo ou com segredo errado; usuário inativo | `{"detail": "..."}` |
| **403** | Perfil sem permissão | `{"detail": "Sem permissão para esta ação"}` |
| **404** | Recurso inexistente | `{"detail": "..."}` |
| **409** | Duplicidade (`documento`, `email`) | `{"detail": "..."}` |
| **422** | Validação Pydantic | `{"detail": [ ... ]}` |
| **502** | Falha ao falar com Evolution API | `{"detail": "<str(e)>"}` — **vaza detalhe interno** |

Toda resposta de erro é `{"detail": string}` exceto 422, que é a lista padrão do Pydantic.

## Endpoints

### Autenticação — `/auth`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/login` | — | Login. Devolve `{access_token, refresh_token, token_type}`. 401 se credencial errada ou conta inativa. |
| POST | `/auth/refresh` | — | Recebe refresh, devolve par novo. 401 se `typ != refresh`. |
| GET | `/auth/me` | JWT | Usuário autenticado. |
| PATCH | `/auth/password` | JWT | Troca a própria senha. Exige `senha_atual`. 204. |

### Usuários — `/auth/usuarios`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/auth/usuarios` | admin, supervisor | Lista, ordenada por nome. |
| POST | `/auth/usuarios` | admin, supervisor | Cria. Supervisor só pode criar `atendente`. 409 se email existe. 201. |
| GET | `/auth/usuarios/{id}` | admin, supervisor | Detalhe. |
| PATCH | `/auth/usuarios/{id}` | admin, supervisor | Atualiza. Só admin altera `perfil`. |
| DELETE | `/auth/usuarios/{id}` | **admin** | Soft delete (`ativo = false`). 204. |

### Clientes — `/clientes`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/clientes` | JWT | Lista paginada. Filtros `nome`, `documento` (substring, em memória). |
| GET | `/clientes/{id}` | JWT | Detalhe. |
| POST | `/clientes` | admin, supervisor | Cria. 409 em `documento` duplicado. 201. |
| PATCH | `/clientes/{id}` | admin, supervisor | Atualização parcial. |
| GET | `/clientes/{id}/lojas` | JWT | Lojas do cliente. |
| POST | `/clientes/{id}/lojas` | admin, supervisor | Adiciona loja. 201. |

### Chats — `/chats`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/chats` | JWT | Lista paginada. Filtros `status`, `cliente_id`, `prioridade`. **Visibilidade filtrada por perfil.** |
| GET | `/chats/{id}` | JWT | Detalhe. |
| POST | `/chats` | JWT | Cria. Default `NOVO` / `media`. 201. |
| PATCH | `/chats/{id}/status` | JWT | Transição. Valida contra `STATUS_TRANSITIONS`. 400 se inválida. |
| PATCH | `/chats/{id}/assinar` | admin, supervisor | Atribui atendente. |
| PATCH | `/chats/{id}/prioridade` | admin, supervisor | Define prioridade. |
| PATCH | `/chats/{id}/pegar` | JWT | Auto-atribuição. 400 se já pertence a outro. |
| PATCH | `/chats/{id}/transferir` | JWT | Transfere para atendente. Atendente só transfere o próprio. |
| PATCH | `/chats/{id}/transferir-grupo` | JWT | Transfere para setor. Limpa `atendente_id`. |

### Mensagens — `/chats/{chat_id}/mensagens`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/chats/{chat_id}/mensagens` | JWT | Histórico paginado. Default 100, máximo 500. |
| POST | `/chats/{chat_id}/mensagens` | JWT | Salva. Se `remetente = atendente` e o chat tem `whatsapp_number`, **envia pelo WhatsApp**. 502 se o envio falhar. 201. |

### WhatsApp — `/chats`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/chats/enviar-whatsapp` | JWT | Inicia conversa por número: localiza ou cria cliente, reutiliza o chat aberto mais recente ou cria um, salva a mensagem, envia, broadcast. 201. |

### Kanban — `/kanban`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/kanban` | JWT | 7 colunas, cards ordenados por prioridade e data. Visibilidade filtrada. |
| PATCH | `/kanban/mover` | JWT | Move card. Delega a `ChatService`, então a máquina de estados **aplica**. 204. |

### Dashboard — `/dashboard`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/dashboard` | JWT | 8 KPIs, contagem por status (8 colunas), 10 chats recentes. **Sem filtro de visibilidade.** |

### Base de conhecimento — `/knowledge-base`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/knowledge-base` | JWT | Lista artigos ativos. Filtro `categoria`. |
| GET | `/knowledge-base/{id}` | JWT | Detalhe. |
| POST | `/knowledge-base` | admin, supervisor | Cria. **Não indexa no Qdrant.** 201. |
| PATCH | `/knowledge-base/{id}` | admin, supervisor | Atualiza. **Não reindexa.** |
| DELETE | `/knowledge-base/{id}` | admin, supervisor | Remove. **Não remove o vetor.** 204. |

### IA — `/ai`

Autenticado por **JWT**. Consumido por operador humano, não pelo n8n.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/ai/classificar` | Classifica uma mensagem em categoria ERP + subcategoria + confiança. Cache Redis. |
| POST | `/ai/analisar` | Sumariza (`tipo=summarizar`) ou diagnostica (`tipo=diagnosticar`) o histórico de um chat. **Não persiste.** |
| POST | `/ai/solucionar` | Busca no RAG e gera solução. **Atualiza o chat** (status, solução, `necessita_humano`). |

> **Todos os três usam query parameter, não body.** `/ai/classificar?mensagem=...`,
> `/ai/analisar?chat_id=...&tipo=...`, `/ai/solucionar?chat_id=...`. O conteúdo da
> mensagem do cliente fica na URL, e portanto em access log. Ver gap 03-4.

> `/ai/solucionar` **escreve no chat e ignora a máquina de estados.** Ver gap 03-5.

### Webhooks (n8n) — `/webhooks`

Todas exigem `X-Webhook-Secret`. Nenhuma aceita JWT.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/webhooks/mensagem` | Mensagem recebida. Cria cliente e chat se não existirem. 201. |
| PATCH | `/webhooks/chat/status` | Define status. **Não valida transição.** |
| POST | `/webhooks/chat/diagnostico` | Persiste diagnóstico e espelha nos campos do chat. |
| PATCH | `/webhooks/cliente/{chat_id}` | Atualiza campos do cliente (whitelist). |
| GET | `/webhooks/chat/{chat_id}/contexto` | Contexto mínimo para o agente de IA. |

O payload de `/webhooks/mensagem` aceita **dois formatos**: o achatado que o n8n monta
(`whatsapp_number`, `conteudo`) e o payload bruto da Evolution API
(`data.key.remoteJid`, `data.message.conversation`). A normalização fica em
`_normalizar_payload` (`backend/app/api/routes/webhooks.py`).

### WebSocket — `/ws/chat/{chat_id}`

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| WS | `/ws/chat/{chat_id}?token=<jwt>` | JWT em query param | Canal de eventos do chat. |

- Token inválido ou `typ != access` → fechamento `1008` (Policy Violation).
- Eventos emitidos: `nova_mensagem`, `status_update`, `diagnostico`. Envelope
  `{event, data}`.
- O JWT viaja na **query string** — vaza em log de acesso e proxy. Ver gap 03-6.

### Operação

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/health` | — | `{"status": "ok"}`. Alvo do HEALTHCHECK do Dockerfile. |
| GET | `/settings/ia-name` | — | Nome da IA exibido no painel. |

### Evolution API — `/evolution`

Todas as rotas exigem **admin** (dependência no nível do router).

| Método | Rota | Descrição |
|---|---|---|
| POST | `/evolution/instance` | Cria instância (Baileys). |
| GET | `/evolution/instance/qrcode/{name}` | QR code / pareamento. |
| GET | `/evolution/instance/status/{name}` | Estado da conexão. |
| POST | `/evolution/instance/webhook/{name}` | Define webhook (URL e eventos). |
| POST | `/evolution/instance/webhook/default/{name}` | Define webhook com URL padrão do n8n. |
| POST | `/evolution/send-text/{name}` | Envia texto. |
| POST | `/evolution/instance/disconnect/{name}` | Desconecta. |

Falha ao falar com a Evolution → **502** com `str(e)` no `detail`.

## Regras transversais

1. **Paginação** — `skip` e `limit`. A resposta traz o total. Teto: 200 para clientes,
   500 para mensagens. Acima do teto, é **erro**, não truncamento silencioso.
2. **Filtro de substring** — `nome` e `documento` de cliente casam por substring em
   memória, não por índice. Case-insensitive.
3. **Visibilidade de chat** — atendente vê apenas: chats sem atendente atribuído cujo
   `setor_alvo` bate com o seu setor, mais os chats que já são seus. Admin e supervisor
   veem tudo. Aplicado em `GET /chats` e `GET /kanban`. **Não** aplicado em
   `GET /chats/{id}`, `GET /dashboard`, `GET /chats/{id}/mensagens`.
4. **Envio de mensagem acopla escrita e envio** — se a Evolution falhar, a mensagem já
   foi persistida e o endpoint devolve 502. O atendente vê erro mas a mensagem está no
   histórico. Isso evita perder texto do usuário; o custo é mensagem duplicada se ele
   reenviar.
5. **Broadcast WebSocket** — toda rota que altera chat ou mensagem deve emitir evento.
   hoje `POST /chats/{id}/mensagens` e o webhook de mensagem emitem; `PATCH
   /chats/{id}/status`, `pegar`, `transferir` **não**.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 03-1 | `GET /dashboard` não aplica filtro de visibilidade. Atendente vê contagem global e nome dos clientes dos 10 chats mais recentes, inclusive de outros setores | `dashboard.py` | **Alta** | **ABERTO** → [04-rbac-matrix](04-rbac-matrix.md) |
| 03-2 | `GET /chats/{id}`, `GET /chats/{chat_id}/mensagens` e `GET /clientes/{id}` não checam posse. O filtro existe só nas rotas de lista | `chats.py`, `mensagens.py`, `clientes.py` | **Alta** | **ABERTO** |
| 03-3 | `PATCH /webhooks/chat/status` ignora `STATUS_TRANSITIONS`. Permite sair de `ENCERRADO` e qualquer caminho impossível. Quem tem o segredo pode forçar estado | `webhooks.py` | **Alta** | **ABERTO** → [01-domain-glossary](01-domain-glossary.md) |
| 03-4 | `/ai/*` usa query parameter para conteúdo de cliente. Vaza PII e prompt em access log | `ai/router.py:31,48,73` | **Alta** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 03-5 | `/ai/solucionar` escreve no chat via repositório, furando a máquina de estados. E o `except Exception: pass` engole falha de persistência sem log | `ai/router.py:118-140` | **Alta** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 03-6 | JWT do WebSocket viaja em query param → log de acesso, proxy, histórico | `main.py` (rota WS) | **Alta** | **ABERTO** → [08-non-functional](08-non-functional.md) |
| 03-7 | 502 devolve `str(e)` do `httpx`, expondo URL interna e corpo do erro da Evolution | `routes/evolution.py`, `routes/mensagens.py` | Média | **ABERTO** |
| 03-8 | Rotas que alteram chat não emitem evento WebSocket: `status`, `pegar`, `transferir`, `transferir-grupo`, `assinar`, `prioridade`. O painel só reflete por polling | `chats.py`, `kanban.py` | Média | **ABERTO** |
| 03-9 | `POST /chats/{id}/assinar` existe e é admin/supervisor, mas o frontend nunca chama. O caminho real é `pegar`/`transferir` | `chats.py`; sem chamador em `frontend/` | Baixa | **ABERTO** |
| 03-10 | `POST /auth/refresh` e `PATCH /auth/password` existem no backend e **nunca** são chamados pelo frontend | `auth.py`; sem chamador em `frontend/` | **Alta** | **ABERTO** → [07-frontend](07-frontend.md) |
| 03-11 | `POST /chats/enviar-whatsapp` tem lógica de negócio **dentro da rota** (localizar/criar cliente, reutilizar chat, salvar, enviar, broadcast). Não é testável isoladamente nem reaproveitável | `routes/mensagens.py` | Média | **ABERTO** |
| 03-12 | `GET /atendentes/ativos` tem a lógica **dentro da rota**. Sem serviço | `routes/atendentes.py` | Baixa | **ABERTO** |
| 03-13 | `EvolutionService.criar_instancia` engole 403 e devolve resposta fabricada sem QR code. O painel recebe 200 e fica esperando um QR que não virá | `evolution_service.py` | Média | **ABERTO** |
| 03-14 | `POST /evolution/instance/webhook/default/{name}` tem a URL do n8n **hardcoded**, e ela não bate com o path real do workflow | `routes/evolution.py` vs `workflow-support-ai.json` | **Alta** | **ABERTO** → [06-n8n-workflow](06-n8n-workflow.md) |
| 03-15 | Nome da instância Evolution `"emsoft-support"` está hardcoded em três lugares e não é configurável | `routes/mensagens.py` ×2, `routes/evolution.py` | Média | **ABERTO** |
| 03-16 | `WEBHOOK_SECRET` não é validado no startup. App sobe com todos os webhooks permanentemente em 401 | `core/config.py:50-57` | Média | **ABERTO** → [09-infra-deploy](09-infra-deploy.md) |
| 03-17 | `GET /settings/ia-name` é público e não requer autenticação | `main.py` | Baixa | **ABERTO** |
| 03-18 | `POST /webhooks/chat/diagnostico` e `GET /webhooks/chat/{id}/contexto` **não têm chamador** | `webhooks.py` | Média | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
# SPEC 03 — Contrato da API FastAPI

## Convenções

- FastAPI; prefixo global atual na raiz.
- JSON UTF-8; datas ISO-8601 UTC.
- Erros seguem `{"detail": "..."}`; 422 segue validação Pydantic.
- Nunca devolver stack trace, token externo ou payload sensível.
- Serviços de domínio fazem validação e autorização; routes apenas validam DTO e encaminham.
- Não fazer chamada à API Emsoft diretamente em handlers de request de usuário quando isso puder ser executado pela outbox.

## Autenticação

### Usuários humanos

`Authorization: Bearer <access_token>`. Validar assinatura, expiração e claim `typ=access`; reler usuário do Appwrite e validar `ativo`. Perfil do token não substitui a fonte persistida.

### n8n / webhooks

`X-Webhook-Secret: <WEBHOOK_SECRET>` em todas as rotas `/webhooks/**`, comparação em tempo constante. Sem segredo configurado, falhar fechado com 401.

### Worker de integração

Worker interno não usa JWT de atendente nem o segredo do n8n. Executa dentro do backend com configuração de serviço e credencial Emsoft no servidor. Não expor endpoint público que permita ao cliente chamar diretamente a integração.

## Endpoints existentes — manter compatibilidade

| Método | Rota | Permissão | Responsabilidade |
|---|---|---|---|
| POST | `/auth/login` | Pública | Login JWT |
| POST | `/auth/refresh` | Refresh token | Renovar par de tokens |
| GET | `/auth/me` | JWT | Perfil atual |
| GET/POST | `/auth/usuarios` | Admin/supervisor | Listar/criar usuários |
| GET/PATCH/DELETE | `/auth/usuarios/{id}` | Conforme RBAC | Detalhar/editar/desativar |
| GET/POST | `/clientes` | JWT / admin-supervisor para criação | Clientes |
| GET/PATCH | `/clientes/{id}` | JWT / admin-supervisor para edição | Cliente |
| GET/POST | `/chats` | JWT | Listar/criar chats |
| GET | `/chats/{id}` | JWT | Detalhe |
| PATCH | `/chats/{id}/status` | JWT conforme transição | Alterar estado pelo serviço de domínio |
| PATCH | `/chats/{id}/assinar` | Admin/supervisor | Atribuição explícita |
| PATCH | `/chats/{id}/pegar` | JWT | Atendente assume chat disponível |
| PATCH | `/chats/{id}/transferir` | JWT | Transferir para atendente |
| PATCH | `/chats/{id}/transferir-grupo` | JWT | Rota legada para setor |
| GET/POST | `/chats/{id}/mensagens` | JWT | Histórico e envio |
| GET | `/kanban` | JWT | Kanban com escopo de visibilidade |
| GET | `/dashboard` | JWT | KPIs filtrados pelo escopo de acesso |
| CRUD | `/knowledge-base` | JWT/admin-supervisor para escrita | Artigos |
| POST | `/webhooks/mensagem` | X-Webhook-Secret | Receber mensagem Evolution |
| POST | `/webhooks/chat/diagnostico` | X-Webhook-Secret | Registrar diagnóstico |
| GET | `/webhooks/chat/{id}/contexto` | X-Webhook-Secret | Contexto mínimo para processamento IA |

Atualizar endpoints existentes para obedecer à máquina de estados; nenhum endpoint de status pode fazer update direto ignorando `STATUS_TRANSITIONS`.

## Novos endpoints de departamento

| Método | Rota | Permissão | Descrição |
|---|---|---|---|
| GET | `/departamentos` | JWT | Lista departamentos ativos; admin/supervisor podem incluir inativos via filtro |
| POST | `/departamentos` | Admin | Criar departamento |
| GET | `/departamentos/{id}` | JWT | Detalhe |
| PATCH | `/departamentos/{id}` | Admin | Editar nome, descrição, ordem e flags; código exige migração se já referenciado |
| DELETE | `/departamentos/{id}` | Admin | Preferir desativação; não apagar se houver chats/usuários/regras vinculados |
| GET | `/departamentos/{id}/atendentes` | Admin/supervisor | Atendentes ativos do departamento |

## Novos endpoints de roteamento

| Método | Rota | Permissão | Descrição |
|---|---|---|---|
| PATCH | `/chats/{id}/transferir-departamento` | JWT conforme RBAC | Transferir para departamento por ID; limpa atendente atual |
| PATCH | `/chats/{id}/atribuir-atendente` | Admin/supervisor ou regra de autoatribuição | Atribuir atendente; mantém departamento e valida compatibilidade |
| GET | `/chats/{id}/roteamento` | JWT com acesso ao chat | Exibir intenção, categoria, departamento sugerido/final e motivo |
| POST | `/ai/classificar-intencao` | JWT/serviço interno | Classificar intenção a partir do chat/mensagem; não executar transferência |

`/chats/{id}/transferir-grupo` continua disponível temporariamente como alias de compatibilidade, mas recebe/responde IDs de departamento após migração. Não adicionar novos usos de string `setor`.

## Integração externa — consulta e reprocessamento

| Método | Rota | Permissão | Descrição |
|---|---|---|---|
| GET | `/integracoes/chamados/{chat_id}` | Admin/supervisor; atendente do chat pode ver status limitado | Estado do vínculo externo e último erro sanitizado |
| POST | `/integracoes/chamados/{chat_id}/reprocessar` | Admin/supervisor | Solicitar novo evento seguro para sincronizar; não aceitar payload arbitrário |
| GET | `/integracoes/chamados/pendentes` | Admin/supervisor | Lista paginada de erros/pendências |

Não expor endpoint para fornecer token ou payload arbitrário à API externa. A criação/atualização é acionada por eventos de domínio processados pelo worker.

## DTOs principais

### Classificação de intenção — resposta interna

```json
{
  "intencao": "solicitacao_financeira",
  "subintencao": "negociacao",
  "categoria_erp": null,
  "departamento_sugerido_codigo": "financeiro",
  "confianca": 0.96,
  "motivo": "O cliente solicita negociação de uma pendência."
}
```

O modelo pode sugerir `departamento_sugerido_codigo`; o backend precisa validar existência, ativação e regra. Não aceitar nome de departamento livre como destino final.

### Transferência de departamento

```json
{
  "departamento_id": "<appwrite-document-id>",
  "motivo": "Solicitação financeira identificada pela triagem",
  "preservar_atendente_se_compativel": false
}
```

### Atribuição humana

```json
{
  "atendente_id": "<appwrite-document-id>",
  "motivo": "Atendente assumiu a conversa"
}
```

### Estado da integração

```json
{
  "chat_id": "<id-local>",
  "sistema_externo": "EMSOFT_CHAMADOS",
  "chamado_id_externo": "<id-retornado-pela-api>",
  "responsavel_tipo": "HUMANO",
  "status_integracao": "SINCRONIZADO",
  "ultima_sincronizacao_em": "2026-11-06T13:00:00Z"
}
```

## Códigos de erro

- 400: transição inválida ou atribuição incompatível.
- 401: credencial ausente/inválida, usuário inativo ou webhook sem segredo.
- 403: perfil sem permissão ou chat fora do escopo.
- 404: chat, usuário ou departamento inexistente.
- 409: duplicidade lógica/conflito de atribuição ou departamento ainda referenciado.
- 422: DTO inválido.
- 502: falha imediata em integração síncrona; evitar este padrão para sincronização Emsoft via outbox.
- 503: serviço interno indisponível quando a operação não pode ser aceita.

## Segurança dos contratos

- Não enviar texto de mensagem como query parameter; usar POST JSON para evitar vazamento em access logs.
- Não colocar JWT em query string do WebSocket em nova implementação; adotar autenticação por mecanismo seguro compatível com a infraestrutura/proxy.
- Aplicar paginação e filtro de visibilidade também no dashboard.
- Redigir erros externos antes de devolver/logar; tokens, documentos e dados pessoais não devem aparecer em logs.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 03-1 | `GET /dashboard` não aplica filtro de visibilidade | `api/routes/dashboard.py:11-17` | **Alta** | **CORRIGIDO** — `routes/dashboard.py` passa `user` (mesma correção de 04-1) |
| 03-2 | `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse | `api/routes/chats.py:36-43`; `mensagens.py`; `clientes.py` | **Alta** | **CORRIGIDO** — mesma correção de 04-2 |
| 03-3 | `PATCH /webhooks/chat/status` ignora `STATUS_TRANSITIONS` | `services/webhook_service.py:79-86` | **Alta** | **CORRIGIDO** (2026-11-10) — mesma raiz de 01-2: webhook delega para `ChatService.atualizar_status` (validação de `STATUS_TRANSITIONS`) → [01](01-domain-glossary.md) |
| 03-4 | `/ai/*` usa query parameter para conteúdo do cliente (PII em access log) | `ai/router.py:34-54` | **Alta** | **CORRIGIDO (rota nova)** — `/ai/classificar-intencao` usa body JSON; `/ai/classificar` e `/ai/analisar` legados seguem com query param |
| 03-5 | `/ai/solucionar` escrevia no chat furando a máquina de estados | `ai/router.py` | **Alta** | **CORRIGIDO** — delega a `AIPipelineService`/`ChatService` |
| 03-6 | JWT do WebSocket viajava em query string | `api/websocket_manager.py` | **Alta** | **CORRIGIDO** — token na 1ª mensagem (fallback legado ainda aceito) |
| 03-7 | 502 devolve `str(e)` do `httpx`, expondo URL/corpo da Evolution | `api/routes/mensagens.py:55-59,111-115`; `evolution.py` | Média | **ABERTO** |
| 03-8 | Rotas que alteram chat não emitem evento WebSocket (`status`, `pegar`, `transferir`, `assinar`, `prioridade`, kanban `mover`) | `api/routes/chats.py`, `kanban.py` | Média | **ABERTO** |
| 03-9 | `POST /chats/{id}/assinar` existe (admin/supervisor) sem chamador no frontend | `api/routes/chats.py:67-75` | Baixa | **ABERTO** |
| 03-10 | `/auth/refresh` e `PATCH /auth/password` existem e não são chamados pelo frontend | `api/routes/auth.py` | **Alta** | **CORRIGIDO** (2026-11-10) — frontend persiste `refresh_token` e renova via `POST /auth/refresh` em 401 (retry único); decisão: `PATCH /auth/password` segue sem chamador no frontend (troca de senha fora do escopo do produto) → [07](07-frontend.md) |
| 03-11 | `POST /chats/enviar-whatsapp` tem lógica de negócio dentro da rota | `api/routes/mensagens.py:69-122` | Média | **ABERTO** |
| 03-12 | `GET /atendentes/ativos` tem a lógica dentro da rota | `api/routes/atendentes.py` | Baixa | **ABERTO** |
| 03-13 | `EvolutionService.criar_instancia` engole 403 e devolve resposta fabricada sem QR | `services/evolution_service.py:31-34` | Média | **ABERTO** |
| 03-14 | Webhook padrão da Evolution aponta para URL hardcoded `/webhook/emsoft-whatsapp` | `api/routes/evolution.py:86` | **Alta** | **ABERTO** → [06](06-n8n-workflow.md) |
| 03-15 | Nome da instância `"emsoft-support"` hardcoded em mensagens/evolution | `api/routes/mensagens.py:51,107`; `evolution_service.py:25` | Média | **ABERTO** |
| 03-16 | `WEBHOOK_SECRET` sem validação no startup | `core/config.py:50-62` | Média | **CORRIGIDO** — `validate_production_secrets` exige segredo em produção |
| 03-17 | `GET /settings/ia-name` é público e não requer autenticação | `main.py:85-87` | Baixa | **ABERTO** |
| 03-18 | `/webhooks/chat/diagnostico` sem chamador (`/contexto` já é chamado pelo n8n) | `api/routes/webhooks.py` | Média | **ABERTO** → [05](05-ai-pipeline.md) |
| 03-19 | Endpoints-alvo inexistentes: `/departamentos*`, `/chats/{id}/transferir-departamento`, `/atribuir-atendente`, `/roteamento`, `/ai/classificar-intencao`, `/integracoes/chamados/*` | `api/routes/` | **Alta** | **ABERTO (parcial)** — `/departamentos*`, `/chats/{id}/transferir-departamento`, `/atribuir-atendente`, `/roteamento` e `/integracoes/chamados/*` (scaffold 11-1) implementados; falta apenas `/ai/classificar-intencao` (classificação segue interna ao pipeline, sem rota) |

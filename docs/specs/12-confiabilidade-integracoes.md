# SPEC 12 — Confiabilidade, Outbox, Idempotência e Reprocessamento

## Objetivo

Garantir que mensagens, transições de atendimento e sincronização de chamados externos sejam tolerantes a retries, timeouts e reinicialização de processo sem criar duplicatas ou perder eventos.

## Outbox pattern

Sempre que uma transição local exigir sincronização externa:

1. Validar a operação no serviço de domínio.
2. Persistir a alteração do chat/diagnóstico.
3. Persistir registro `integration_outbox` com `event_key` determinística.
4. Retornar ao fluxo de atendimento sem aguardar a API externa.
5. Worker busca eventos pendentes com lock/lease.
6. Worker chama `EmsoftChamadosIntegrationService`.
7. Em sucesso, atualiza `integracao_chamados` e marca outbox `CONCLUIDO`.
8. Em erro transitório, agenda retry com backoff.
9. Em erro permanente ou ambíguo não reconciliável, marca `FALHA_PERMANENTE` e alerta operador.

Como Appwrite não oferece necessariamente transação multi-documento, implementar a ordem de persistência e reconciliação de modo que eventos não sejam perdidos. Para operações críticas, usar identificadores determinísticos e um job de auditoria que compare chats elegíveis sem vínculo/outbox.

## Tipos de evento

- `TICKET_CREATE_REQUESTED`
- `TICKET_UPDATE_REQUESTED`
- `TICKET_ASSIGNMENT_CHANGED`
- `TICKET_RESOLUTION_REQUESTED`
- `TICKET_REOPEN_REQUESTED`

Não criar evento por mensagem comum sem mudança relevante. Mudanças repetidas idênticas devem deduplicar.

## Idempotency keys

Formatos lógicos sugeridos:

- Criação: `emsoft:create:{chat_id}`
- Atualização por versão do agregado: `emsoft:update:{chat_id}:{event_version}`
- Atribuição: `emsoft:assign:{chat_id}:{assignment_version}`
- Resolução: `emsoft:resolve:{chat_id}:{resolution_version}`

A chave externa somente será enviada se a API Emsoft suportar o mecanismo. Internamente, `event_key` é obrigatória e única pela aplicação.

## Mensagens Evolution

Deduplicar por instância + `external_message_id`. A persistência deve ocorrer antes do processamento IA. Eventos reenviados não devem repetir:

- insert da mensagem;
- resposta ao WhatsApp;
- análise IA;
- evento de criação/atualização de chamado.

## Política de retry

- Timeout/conexão/429/5xx: retry com backoff exponencial, jitter e máximo configurável.
- 400/422: erro de payload; não repetir sem alteração.
- 401/403: falha de credencial/permissão; parar retries agressivos e alertar admin.
- 404: reconciliar ID externo; não criar registro automaticamente sem decisão.
- 409: consultar se o recurso já existe ou se existe conflito de versão.
- Timeout com criação possivelmente aplicada: executar reconciliação antes de novo POST.

## Concorrência

- Só um worker pode processar um `event_key` por vez.
- Lock deve expirar em caso de queda de worker e permitir recuperação.
- Antes de aplicar update externo, revalidar a versão/estado atual do chat para evitar enviar dados obsoletos.
- Eventos antigos de atribuição não podem sobrescrever responsável mais recente. Usar versão sequencial/timestamp monotônico e descartar eventos obsoletos.

## Reprocessamento manual

Admin/supervisor pode solicitar retry por chat. O endpoint não recebe payload livre: cria evento novo/reaproveita evento conforme tipo e versão atual, preservando auditoria. Deve mostrar motivo, ator e data.

## Reconciliação periódica

Job periódico procura:

- chat elegível sem registro `integracao_chamados`;
- integração marcada `PENDENTE` além do limite;
- outbox parada em `PROCESSANDO` com lease expirado;
- integração com `chamado_id_externo` mas status local inconsistente;
- responsável local sem mapeamento externo.

A reconciliação não cria ticket quando a existência externa é ambígua; gera pendência para revisão.

## Retenção e auditoria

Manter histórico suficiente de tentativas, erros, event keys e IDs externos conforme política interna. Não armazenar headers secretos ou payloads com credenciais. Payload pode conter dados pessoais do cliente; restringir acesso e aplicar retenção.

## Critérios de aceite

- Retry de mesmo evento não cria ticket duplicado.
- Timeout após POST não dispara novo POST cego.
- Worker reiniciado retoma eventos com lease expirado.
- Evento antigo não substitui atribuição nova.
- Falha externa não muda indevidamente status do chat.
- Painel informa integração pendente/erro com ação autorizada de reprocessamento.
- Logs possuem correlation/event key e não possuem segredo.

## Registro de Gaps

Verificado contra o código em 2026-11-06; re-verificado em 2026-11-10 — 12-1 a 12-7 implementados. Nota de rastreio: o commit `28157e4` rotulou a implementação da `event_key` como 12-2, mas ela corresponde a 12-3; e o commit `af5c0a4` cobre 12-2 (lease) e 12-4 (backoff+jitter).

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 12-1 | Coleção `integration_outbox` inexistente | `appwrite/schema.py` (L281) + `appwrite/repositories/integration_outbox.py` | **Alta** | **CORRIGIDO** |
| 12-2 | Worker/lock/lease de outbox inexistente | `integrations/outbox/worker.py` (lease `lease_owner`/`lease_expires_at`) | **Alta** | **CORRIGIDO** |
| 12-3 | `event_key` determinística/idempotency key inexistente | `integrations/outbox/keys.py` + enums em `models/outbox.py` | **Alta** | **CORRIGIDO** |
| 12-4 | Timeout/retry/backoff+jitter de integrações externas inexistentes | `integrations/outbox/worker.py` (backoff exponencial + jitter; classificação transitória/permanente) | **Alta** | **CORRIGIDO** |
| 12-5 | Reconciliação de timeout ambíguo inexistente | `integrations/outbox/worker.py` (re-PATCH pelo ID; reconciliação no boot, nunca re-POST cego) | **Alta** | **CORRIGIDO** |
| 12-6 | Logs sem correlation/event key | `integrations/outbox/worker.py` (logs com `event_key`/`chat_id`, sem payload livre) | Média | **CORRIGIDO** → 08-5 |
| 12-7 | Sem painel de pendência/reprocessamento para operador | `api/routes/integracoes.py` (GET /pendentes, GET /{chat_id}, POST /{chat_id}/reprocessar) | Média | **CORRIGIDO** → 03, 07 |

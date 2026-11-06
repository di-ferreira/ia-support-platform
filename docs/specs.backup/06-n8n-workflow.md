# SPEC 06 — Workflow n8n

O n8n é o **orquestrador de transporte**. Ele não contém prompt de negócio nem decisão:
recebe a mensagem da Evolution, chama a API do backend, e entrega a resposta no WhatsApp.
Ver [adr/0004-backend-dono-da-ia.md](adr/0004-backend-dono-da-ia.md).

## Arquivo

`infra/n8n/workflow-support-ai.json` — export versionado, importável. É a única
definição do fluxo. O que está no console do n8n é consequência do import.

`docs/n8n-workflow.md` é o documento narrativo antigo, agora **arquivado** por banner. Ele
descreve um workflow de 12 nós com Qdrant e LLM Chain que **nunca foi implementado**. Ver
gap 06-11.

## Configuração de ambiente

### Credenciais

| Nome no n8n | Tipo | Uso |
|---|---|---|
| Evolution account | Evolution API | `Enviar texto` |
| Ollama account | Ollama | **Remover** — o backend chama o LLM |

Os IDs de credencial no JSON versionado (`MTYK5wjtIxyMTieD`, `KySNjgormc0VStxZ`) são
específicos da instalação de origem. **Não funcionam** numa instalação nova: é preciso
recriar as credenciais pelo nome antes de ativar.

### Variáveis

| Variável | Usada em | Origem |
|---|---|---|
| `WEBHOOK_SECRET` | Header `X-Webhook-Secret` de toda chamada HTTP | `infra/.env` |
| `BACKEND_URL` | URL base de toda chamada HTTP | `infra/.env` |
| `EVOLUTION_INSTANCE` | Nome da instância no nó `Enviar texto` | `infra/.env` |

Acessar env var dentro de nó exige `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`. Sem isso, os
nós HTTP falham com "access to env vars denied". **A variável não está em nenhum
`.env.example` nem compose** — ver gap 06-9.

## Workflow alvo

```
Webhook  ──▶ If (fromMe == false) ──▶ Extrair ──▶ Salvar mensagem ──▶ Contexto
                                                                            │
                                          ┌─────────────────────────────────┤
                                    IA deve responder?                  sim │
                                          │                                 ▼
                                          │              POST /webhooks/ai/solucionar
                                        não │                                 │
                                          │                                 ▼
                                          │                         Salvar resposta IA
                                          │                          (remetente="ia")
                                          │                                 │
                                          └─────────────────────────────────┤
                                                                            ▼
                                                                     Enviar texto
                                                                        (Evolution)
                                                                            │
                                                                            ▼
                                                                    PUSH status/diag
                                                                   (WebSocket n8n)
```

### 1. Webhook

| Campo | Valor |
|---|---|
| Tipo | `n8n-nodes-base.webhook` v2.1 |
| Método | `POST` |
| Path | **legível**: `/webhook/emsoft-whatsapp` |
| Resposta | `202` imediato; o trabalho é assíncrono |

> Hoje o path é o UUID cru `865c14e8-9225-45dc-b5a3-1fa11c99dbaa`. Isso quebra
> `POST /evolution/instance/webhook/default/{name}`, que tem `emsoft-whatsapp` hardcoded.
> Ver gap 06-1.

A Evolution não envia header de autenticação no webhook de entrada. A proteção real é o
`X-Webhook-Secret` nas **saídas** do n8n para o backend. O webhook de entrada é,
essencialmente, aberto a qualquer POST que alcance a porta do n8n.

### 2. If — mensagem recebida vs. enviada

| Campo | Valor |
|---|---|
| Condição | `$json.body.data.key.fromMe` **equals** `false` |
| Saída `true` | seguir o fluxo |
| Saída `false` | **array vazio** — descarta silenciosamente |

`fromMe = true` são as mensagens que **a própria conta enviou**. Descartá-las evita loop:
a resposta da IA voltaria e seria processada de novo.

Risco: qualquer mensagem que o sistema envie usando um número **diferente** da instância
cai em `fromMe = false` e entra no fluxo. Se o atendente responder pelo WhatsApp pessoal
para o mesmo cliente, isso vira mensagem de cliente.

### 3. Extrair dados da mensagem

Extrai, do payload Evolution:

| Campo | Caminho | Fallback |
|---|---|---|
| `remoteJid` | `body.data.key.remoteJid` | — |
| `messageId` | `body.data.key.id` | — |
| `timestamp` | `body.data.messageTimestamp` | — |
| `fromMe` | `body.data.key.fromMe` | `false` |
| Tipo | derivado da chave de `message` | `texto` |
| Conteúdo | `message.conversation` | ver tabela abaixo |

**Mapeamento de conteúdo por tipo.** Hoje só `conversation` é lida, então imagem, áudio e
documento chegam como `undefined` e a mensagem é salva vazia:

| Tipo | Caminho de texto | Tem mídia |
|---|---|---|
| Texto | `message.conversation` | não |
| Texto extenso | `message.extendedTextMessage.text` | não |
| Legenda de mídia | `message.imageMessage.caption`, `.videoMessage.caption` | sim |
| Áudio | — (transcrever depois) | sim |
| Documento | `message.documentMessage.caption` | sim |
| Sticker | `message.stickerMessage` | sim |

**Backend já aceita o payload bruto.** `_normalizar_payload` em
`backend/app/api/routes/webhooks.py` normaliza tanto o formato achatado quanto o bruto da
Evolution. Então o nó 3 tem duas opções:

- **A** — montar o payload achatado no n8n (como hoje).
- **B** — repassar o payload bruto direto para `/webhooks/mensagem`.

A opção B é menos código no n8n e mais difícil de errar. **Recomendada.**

### 4. Salvar mensagem

```http
POST {BACKEND_URL}/webhooks/mensagem
X-Webhook-Secret: {WEBHOOK_SECRET}

{ "chat_id": "<id, opcional>", "whatsapp_number": "...", "remetente": "cliente",
  "conteudo": "...", "tipo": "texto", "url_arquivo": null }
```

Devolve `{ chat_id, ... }`. Se `chat_id` não vier, o backend localiza pelo número; se
também não, cria o cliente e o chat.

### 5. Contexto — a IA deve responder?

```http
GET {BACKEND_URL}/webhooks/chat/{chat_id}/contexto
X-Webhook-Secret: {WEBHOOK_SECRET}
```

| `status` do chat | IA responde? | Por quê |
|---|---|---|
| `NOVO` | **sim** | Chat acabou de chegar |
| `IA_ANALISANDO` | **sim** | Re-análise (cliente pediu mais detalhe) |
| `AGUARDANDO_CLIENTE` | **sim** | Cliente respondeu |
| `EM_ATENDIMENTO` | não | Humano tem o chat |
| `AGUARDANDO_HUMANO_COM_SOLUCAO` | não | Já na fila com receita pronta |
| `AGUARDANDO_HUMANO_SEM_SOLUCAO` | não | Humano está investigando |
| `RESOLVIDO` | **sim** | Cliente voltou com "ainda não funciona" |
| `ENCERRADO` | não | Terminal |

`RESOLVIDO` reabrir é o que mantém um chat resolvido de verdade. Mas cuidado: a máquina de
estados tem `RESOLVIDO → ENCERRADO` apenas. Reabrir exige `RESOLVIDO → IA_ANALISANDO`, que
**não existe** na tabela. Ver gap 06-2.

### 6. POST /webhooks/ai/solucionar

```http
POST {BACKEND_URL}/webhooks/ai/solucionar
X-Webhook-Secret: {WEBHOOK_SECRET}

{ "chat_id": "<ulid>" }
```

O backend decide o cenário, grava o diagnóstico e transiciona o status. Resposta em
[05-ai-pipeline](05-ai-pipeline.md) §Contrato.

Este nó **substitui** o `AI Agent` + `Ollama Chat Model` + `Simple Memory` atuais.

> A memória do `Simple Memory` usa `body.data.key.id` como chave, que é o id da
> **mensagem** — muda a cada mensagem. A janela de 10 turnos nunca recupera histórico.
> Não é um problema depois da migração: o backend monta o histórico a partir da coleção
> `mensagens`, que é a fonte real.

### 7. Salvar resposta da IA

```http
POST {BACKEND_URL}/webhooks/mensagem
X-Webhook-Secret: {WEBHOOK_SECRET}

{ "chat_id": "...", "whatsapp_number": "...", "remetente": "ia",
  "conteudo": "{{ $json.mensagem_cliente }}" }
```

`mensagem_cliente` é montado pelo backend. O n8n não redacta nada.

### 8. Enviar texto

| Campo | Valor |
|---|---|
| Tipo | `n8n-nodes-evolution-api.evolutionApi` |
| Resource | `messages-api` |
| Operation | `sendText` |
| `instanceName` | `{{ $env.EVOLUTION_INSTANCE }}` (não hardcoded) |
| `remoteJid` | `{{ ...body.data.key.remoteJid }}` |
| `messageText` | `{{ $json.mensagem_cliente }}` |

### 9. Notificar o painel

```http
POST {BACKEND_URL}/webhooks/chat/status
X-Webhook-Secret: {WEBHOOK_SECRET}

{ "chat_id": "...", "status": "{{ $json.chat_status }}" }
```

Só é necessário se o passo 6 não já tiver aplicado a transição. **Com a arquitetura
alvo, é redundante** — `/webhooks/ai/solucionar` já transiciona e já emite o evento
WebSocket. Ver gap 03-3: essa rota hoje **não** valida a máquina de estados, e é melhor
não depender dela.

## Normalização de número

`remoteJid` chega como `5511999999999@s.whatsapp.net`. O backend remove o sufixo em
`WebhookService.receber_mensagem` (`split("@")[0]`).

**Os dois usos precisam estar consistentes:**

| Uso | Deve mandar |
|---|---|
| `whatsapp_number` no body do backend | o número **com** sufixo é aceito e normalizado |
| `remoteJid` para a Evolution API | o JID **completo**, com sufixo |

Hoje os dois mandam o valor cru. Funciona porque o backend normaliza, mas é frágil:
se a normalização mudar, o envio ao WhatsApp quebra silenciosamente.

## Idempotência

A Evolution reenvia `MESSAGES_UPSERT` em reconexão. Sem proteção, a mesma mensagem do
cliente é persistida **duas vezes**, e a IA responde **duas vezes**.

O workflow atual **não** deduplica. A proteção natural é comparar `messageId` com o
`created_at` da última mensagem do chat — o que exige que o backend exponha o id da
mensagem em `/webhooks/mensagem`. Ver gap 06-3.

## Configuração da Evolution

```bash
POST {EVOLUTION_API_URL}/webhook/set/{EVOLUTION_INSTANCE}
Authorization: Bearer {EVOLUTION_API_KEY}

{ "webhook": { "url": "http://n8n:5678/webhook/emsoft-whatsapp",
               "enabled": true,
               "events": ["MESSAGES_UPSERT"] } }
```

`events` **deve** conter só `MESSAGES_UPSERT`. Incluir `MESSAGE_UPDATE` faz o fluxo
processar toda edição e revogação de mensagem como se fosse nova.

O backend faz isso por `POST /evolution/instance/webhook/default/{name}` — hoje com URL
e nome de instância hardcoded. Ver gap 03-14.

## Tratamento de erro

| Falha | Comportamento desejado |
|---|---|
| Backend fora do ar | Não enviar nada ao cliente. Logar. O cliente recebe resposta no próximo turno |
| `WEBHOOK_SECRET` errado | 401 do backend. O nó deve falhar ruidosamente, não seguir |
| Evolution fora do ar ao enviar | A mensagem **já foi salva** com `remetente = ia`. Reenviar é idempotente do ponto de vista do cliente? **Não** — Evolution pode ter entregado antes de o erro |
| RAG indisponível | O backend deve responder erro, não "sem solução" (gap 05-6) |

O workflow atual não tem tratamento de erro nenhum: `onError` não está configurado em
nenhum nó, então uma falha 502 do backend propaga e o fluxo para.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 06-1 | Path do webhook é o UUID cru `865c14e8-...`. `POST /evolution/instance/webhook/default/{name}` aponta para `/webhook/emsoft-whatsapp`. Os dois não batem | `workflow-support-ai.json:22` vs `routes/evolution.py` | **Alta** | **ABERTO** |
| 06-2 | `RESOLVIDO → IA_ANALISANDO` não existe na máquina de estados, então um cliente que responde "ainda não funciona" em chat resolvido não pode ser reanalisado pela IA | `chat_service.py:8-30` | **Alta** | **ABERTO** → [01-domain-glossary](01-domain-glossary.md) |
| 06-3 | Sem deduplicação. Reconexão da Evolution persiste a mensagem duas vezes e a IA responde duas vezes | `workflow-support-ai.json` | **Alta** | **ABERTO** |
| 06-4 | URL do backend **hardcoded** `http://192.168.3.50:8001` em dois nós. Em produção o n8n roda em container e não alcança a LAN do host | `workflow-support-ai.json:133,168` | **Crítica** | **ABERTO** |
| 06-5 | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` não está em nenhum `.env.example` nem compose. Sem ela, `{{ $env.WEBHOOK_SECRET }}` falha | `docker-compose.dev.yml` | **Crítica** | **ABERTO** |
| 06-6 | Nome da instância `emsoft-support` hardcoded no nó | `workflow-support-ai.json` | Média | **ABERTO** |
| 06-7 | Só `message.conversation` é lido. `extendedTextMessage`, imagem, áudio, documento e legenda de mídia viram `undefined` — o caso mais comum num chamado de ERP (print de tela) é justamente o que não funciona | `workflow-support-ai.json:143` | **Alta** | **ABERTO** |
| 06-8 | `AI Agent` não tem nenhuma tool ligada. O prompt manda "consulte a RAG" mas não há como consultar — o agente alucina | `workflow-support-ai.json:91-107` | **Crítica** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 06-9 | `N8N_ENCRYPTION_KEY` e `N8N_SECURE_COOKIE=false` ausentes. Sem a chave, o n8n deriva do volume e regenera as credenciais se o volume for perdido | `docker-compose.dev.yml` | Média | **ABERTO** → [09-infra-deploy](09-infra-deploy.md) |
| 06-10 | Nenhum nó tem `onError` configurado. Falha 502 do backend para o fluxo inteiro | `workflow-support-ai.json` | **Alta** | **ABERTO** |
| 06-11 | `docs/n8n-workflow.md` descreve 12 nós com Qdrant, LLM Chain e Switch de cenário. O JSON tem 8 nós e nenhum deles. ~70% do doc está errado | `docs/n8n-workflow.md` | Média | **ABERTO** → Fase 5 |
| 06-12 | `docs/n8n-workflow.md:212` descreve chunking 500/50 com `text-embedding-3-small`. Isso quebraria a coleção 768. A decisão real é um vetor por artigo | `docs/n8n-workflow.md` vs `qdrant_service.py:7` | Média | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) §Chunking |
| 06-13 | Workflow está `active: false` no arquivo versionado | `workflow-support-ai.json` | Baixa | **ABERTO** |
| 06-14 | `pinData` do webhook tem `fromMe: true`, que **não passa** pelo `If`. Testar com esse pin dá resultado enganoso | `workflow-support-ai.json:224+` | Baixa | **ABERTO** |
| 06-15 | `docker-compose.dev.yml` não define `extra_hosts: host.docker.internal:host-gateway`, então a rota que `TODO_LIST.md:29` documenta não funciona | `docker-compose.dev.yml` | Média | **ABERTO** |
| 06-16 | `remoteJid` cru é usado tanto no body do backend (que normaliza) quanto na Evolution (que exige o JID completo) | `workflow-support-ai.json:139,178,236` | Média | **ABERTO** |
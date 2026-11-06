# SPEC 06 — Workflow n8n e Transporte WhatsApp

## Responsabilidade do n8n

O n8n é **orquestrador de transporte**: recebe webhooks da Evolution API, encaminha o payload ao backend e envia mensagens que o backend determinou. Não contém prompt de negócio, classificação de intenção, regras de departamento, decisão de cenário, credencial Emsoft ou chamada à API de chamados.

O backend é autoridade para o chat e para integração externa. Ver ADR 0004 e ADR 0007.

## Arquivo de workflow

`infra/n8n/workflow-support-ai.json` é a definição versionada. Alterações no console devem ser exportadas e comitadas. Credenciais/IDs de credencial da instalação de origem não são portáveis; recriar credenciais na instalação de destino.

## Fluxo alvo

1. Webhook recebe `MESSAGES_UPSERT` da Evolution.
2. Filtrar mensagens enviadas pela própria instância (`fromMe=true`) para evitar loop.
3. Preservar `messageId`, `remoteJid`, instância e timestamp.
4. Encaminhar payload bruto, ou formato canônico documentado, para `POST /webhooks/mensagem` com `X-Webhook-Secret`.
5. Backend normaliza payload, deduplica, persiste mensagem e executa/classifica o pipeline quando necessário.
6. Backend devolve a ação necessária: responder, aguardar, pedir esclarecimento ou transferir. O n8n só executa envio quando houver texto destinado ao cliente.
7. Salvar resposta da IA no backend com autoria `ia` se o serviço ainda não a tiver persistido; evitar persistência duplicada. Definir um único proprietário da persistência do output no contrato do webhook.
8. Enviar texto usando Evolution API.
9. O backend emite evento WebSocket para o painel. Não enviar uma segunda alteração de status pelo n8n se o backend já aplicou a transição.

## Payload de entrada canônico

A rota atual aceita payload achatado e payload bruto Evolution. A opção recomendada é repassar o bruto e normalizar apenas no backend. A normalização deve extrair:

- instância e ID da mensagem;
- JID/número do remetente;
- conteúdo textual/legenda;
- tipo de mídia;
- timestamp;
- `fromMe`;
- metadados necessários para rastrear origem.

O backend normaliza número removendo `@s.whatsapp.net` para persistência. Para envio pela Evolution, usar o JID completo exigido pelo provedor.

## Idempotência de mensagens

Evolution pode reenviar evento após reconexão. `messageId` externo deve ser persistido e deduplicado no backend, considerando também a instância. A mesma mensagem não pode gerar duas mensagens internas, duas respostas da IA ou duas solicitações de chamado externo.

Não usar comparação apenas com timestamp como garantia de deduplicação; timestamp pode empatar e não é identidade confiável.

## Credenciais/variáveis n8n

- Credencial Evolution API para envio.
- `BACKEND_URL`.
- `WEBHOOK_SECRET`.
- `EVOLUTION_INSTANCE`.

Não configurar credencial Emsoft no n8n. Não usar credencial Ollama no n8n; o backend chama o provedor LLM. Configurar o acesso a env vars dentro dos nós conforme versão instalada e documentar a configuração em compose/env, nunca hardcode.

## Tipos de mensagem

| Tipo | Entrada | Comportamento |
|---|---|---|
| Texto | conversation/extended text | Persistir e classificar |
| Imagem | image message + caption | Preservar mídia/URL; visão só quando recurso e política estiverem implementados |
| Áudio | audio message | Persistir referência; transcrição é etapa separada e não presumir transcrição disponível |
| Documento | document message + caption | Preservar arquivo e metadados; não executar conteúdo como instrução |
| Sticker/vídeo | payload correspondente | Persistir tipo/referência ou informar formato não suportado; nunca salvar mensagem vazia silenciosamente |

## Falhas

- Falha no backend: n8n deve registrar erro e aplicar retry limitado, respeitando idempotência.
- Falha no envio WhatsApp: persistir estado/erro para reenvio; não duplicar mensagem em backend.
- Falha no Emsoft: não é responsabilidade do n8n; a outbox backend processa e informa painel.
- Evitar loops: mensagens do próprio bot e mensagens enviadas por atendentes devem ser identificadas pelo ID e `fromMe`.

## Configuração da Evolution

Webhook deve receber apenas o evento necessário (`MESSAGES_UPSERT`) para o escopo desta versão. Não incluir `MESSAGE_UPDATE` como nova mensagem, pois edição/revogação não deve iniciar novo atendimento.

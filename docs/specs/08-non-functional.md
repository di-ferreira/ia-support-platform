# SPEC 08 — Requisitos Não Funcionais, Segurança e Observabilidade

## Disponibilidade e degradação

- A plataforma deve continuar recebendo/persistindo mensagens mesmo que o LLM, Qdrant, n8n ou API Emsoft estejam indisponíveis, dentro das limitações de cada fluxo.
- Falha na API Emsoft não pode impedir que um chat seja transferido ou resolvido localmente; persistir evento pendente e informar status.
- Falha no Appwrite impede persistência confiável: não responder ao cliente como se a mensagem tivesse sido registrada.
- Falha no RAG deve resultar em sem solução/encaminhamento, não em orientação inventada.

## Confiabilidade de integrações

- Chamadas HTTP externas com timeout explícito.
- Retentativa apenas para erros transitórios (timeout, conexão, 429, 5xx), com backoff exponencial e jitter.
- Não repetir indiscriminadamente em 4xx de validação/autorização.
- Toda operação de criação de chamado deve possuir idempotency key local e, se API externa suportar, enviar essa chave ao provedor.
- Como não há garantia de idempotência externa confirmada, após timeout ambíguo consultar por referência externa antes de repetir criação; se API não oferecer consulta, colocar em revisão manual ao invés de gerar duplicata automática.
- Retentativas limitadas; depois mover para `FALHA_PERMANENTE` e permitir reprocessamento autorizado.

## Desempenho

- Operações de webhook devem responder rápido depois de persistir a mensagem e agendar trabalho demorado.
- Não aguardar a API Emsoft no request que recebe mensagem WhatsApp.
- Paginar listas; limitar mensagens por página.
- Definir timeouts para Appwrite, Redis, Qdrant, LLM, Evolution e Emsoft via configuração.
- Monitorar latência por dependência separadamente.

## Segurança

- Segredos somente em variáveis de ambiente/secret manager do servidor.
- TLS obrigatório na comunicação com API pública.
- Menor privilégio para API key Appwrite e credenciais Emsoft.
- Não registrar tokens, senhas, Authorization, webhook secrets ou conteúdo sensível em logs.
- Não incluir dados de outros clientes no contexto LLM.
- Validar acesso ao chat no backend em cada rota.
- Proteger webhooks contra segredo ausente/inválido e replay/duplicação por ID de mensagem.
- Limitar tamanho e tipo de anexos; tratar documento como conteúdo não confiável.
- Sanitizar conteúdo exibido na interface para evitar XSS.
- Aplicar política de retenção e acesso mínimo a histórico de conversa.

## Privacidade e dados

- Dados de cliente são usados apenas para atendimento e integração autorizada.
- Não enviar credenciais ou dado bancário para LLM.
- Minimizar dados enviados à API Emsoft ao que é necessário para registrar/atender o chamado.
- Logs devem usar IDs internos e dados mascarados quando possível.
- Registrar finalidade e origem de dados transferidos entre sistemas.

## Observabilidade

Logs estruturados com `correlation_id`, `chat_id`, `event_key`, `integration_id`, sistema externo, resultado e duração. Não incluir segredo nem conteúdo integral.

Métricas mínimas:

- `messages_received_total`, `messages_deduplicated_total`;
- `ai_classification_total` por intenção/resultado;
- `ai_rag_retrieval_latency_seconds`, `ai_solution_confirmed_total`;
- `chat_transfers_total` por departamento;
- `external_ticket_create_total`, `external_ticket_update_total`;
- `external_ticket_sync_failures_total`, `integration_outbox_pending`;
- idade da mensagem/evento pendente mais antigo;
- latência/erro por dependência externa.

Alertar quando fila pendente superar limite configurável, quando houver falha permanente ou quando integração estiver desabilitada em produção sem decisão explícita.

## Métricas do produto

- Taxa de resolução confirmada pela IA = chats com estado final `RESOLVIDO` após orientação IA, sem atribuição humana / chats elegíveis atendidos pela IA.
- Taxa de transbordo = chats transferidos a humano / chats processados.
- Meta de redução operacional: pelo menos 70% sem intervenção humana, sujeita a validação estatística e qualidade.
- Medir precisão do roteamento por correções/mudanças manuais de departamento.
- Chamados externos duplicados: meta zero.

## Recuperação e backup

- Backup Appwrite conforme operação atual.
- Exportar workflows n8n versionados.
- Proteger configurações de integração e segredos em canal distinto dos dados exportados.
- Testar restauração de dados e reprocessamento de outbox em ambiente não produtivo.

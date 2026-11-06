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

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 08-1 | `CORS_ORIGINS` default só `localhost:3000` | `core/config.py:39` | **Alta** | **ABERTO** → [09](09-infra-deploy.md) |
| 08-2 | Comportamento de `verify_webhook` sem segredo não fixado | `api/routes/webhooks.py:32-44` | **Alta** | **CORRIGIDO** — fail-closed (401) e comparação em tempo constante |
| 08-3 | `/health` não checa dependências; sem readiness | `main.py:90-92` | Média | **ABERTO** |
| 08-4 | Sem rate limiting em login/webhooks | `core/rate_limit.py` | **Alta** | **CORRIGIDO** — limiter in-memory (login 60/60s, webhooks 120/60s) |
| 08-5 | Sem logging estruturado nem request-id/correlação | `app/**` | Média | **ABERTO** |
| 08-6 | Sem métricas/tracing/APM; nenhum SLO observável | `app/**` | Média | **ABERTO** |
| 08-7 | `DATABASE_URL` default com credenciais em claro | `core/config.py:10` | Baixa | **ABERTO** |
| 08-8 | WebSocket aceitava token por query string | `api/websocket_manager.py` | **Alta** | **CORRIGIDO** → 07-1 |
| 08-9 | Métricas de produto (resolução confirmada, transbordo, roteamento, duplicidade) sem instrumentação; `tempo_medio_resposta` com semântica errada | `services/dashboard_service.py` | **Alta** | **ABERTO** → 00-10 |
| 08-10 | Degradação da integração Emsoft/outbox não implementada (outbox não existe) | `app/` | **Alta** | **ABERTO** → [12](12-confiabilidade-integracoes.md) |
| 08-11 | Timeout/retry/backoff explícitos de integrações externas não implementados | `services/evolution_service.py` | **Alta** | **ABERTO** → [12](12-confiabilidade-integracoes.md) |
| 08-12 | Health check degradado do bootstrap não implementado | `appwrite/bootstrap.py` | Média | **ABERTO** → 02-10 |

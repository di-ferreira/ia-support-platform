# SPEC 08 — Requisitos não funcionais

Requisitos que atravessam todo o sistema (backend, frontend, infra), independentes de
funcionalidade específica. Deploy/containers fica em [09-infra-deploy.md](09-infra-deploy.md);
estratégia de teste em [10-test-strategy.md](10-test-strategy.md).

## Segurança

### Autenticação

- JWT **HS256** assinado com `SECRET_KEY`. Access token expira em **60 min**; refresh em
  **7 dias** (`config.py:20-21`).
- `SECRET_KEY` tem default inseguro `change-me-in-production`. Em produção,
  `validate_production_secrets()` (chamado no `lifespan`) **bloqueia o boot** se a chave
  for ausente ou o default.
- `algorithm` e os expirations são configuráveis via env.

### Autorização

- RBAC por `perfil` aplicado com `require_perfil` em `app/api/deps.py`. Matriz em
  [04-rbac-matrix.md](04-rbac-matrix.md).
- Rotas de webhook usam secret compartilhado (`verify_webhook`), não JWT.

### Senhas

- Hash no backend (ver [02-data-model.md](02-data-model.md)). Nunca em claro em resposta.

### CORS

- `CORSMiddleware` com `allow_origins=CORS_ORIGINS` (default `http://localhost:3000`),
  `allow_credentials=True`, métodos/headers `*`. Em produção a lista de origens **deve** ser
  restrita ao domínio real — hoje é só localhost. Ver gap 08-1.

### Webhook / M2M

- `WEBHOOK_SECRET` via header `X-Webhook-Secret`. Se ausente em produção, `verify_webhook`
  deve rejeitar — ver [03-api-contract.md](03-api-contract.md) e gap 08-2.

## Configuração e segredos

- Fonte: `pydantic-settings` lendo `.env` (`extra="ignore"`).
- Segredos esperados: `SECRET_KEY`, `APPWRITE_API_KEY`, `EVOLUTION_API_KEY`,
  `OPENAI_API_KEY`, `WEBHOOK_SECRET`, `DATABASE_URL_PROD`.
- `database_url` em clear (postgres) aparece como default no código. Em produção usa
  `DATABASE_URL_PROD` quando `environment=production`.

| Segredo | Default | Risco |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Boot bloqueado em prod (mitigado) |
| `WEBHOOK_SECRET` | `None` | Webhooks 401 — comportamento a validar |
| `APPWRITE_API_KEY` | `""` | API sobe sem Appwrite |
| `EVOLUTION_API_KEY` | `None` | Envio WhatsApp falha |

## Observabilidade

- Logging: stdlib `logging` (`logger = logging.getLogger(__name__)`). Nível e formato
  definidos por `uvicorn`/ambiente; **sem** logger estruturado (JSON) nem correlação de
  request-id.
- **Não há** métricas (Prometheus), tracing (OpenTelemetry) nem APM/Sentry.
- Health: `GET /health` retorna `{"status":"ok"}`. É um liveness simples, não checa
  dependências (Appwrite, Redis, Qdrant, Evolution). Ver gap 08-3.
- Falhas do Appwrite no boot são **best-effort**: a API sobe mesmo com Appwrite fora e tenta
  de novo no próximo boot (`main.py:37-41`).

## Confiabilidade e disponibilidade

- **Sem rate limiting** em nenhuma rota (incl. `/auth/login`, webhooks). Ver gap 08-4.
- **Sem idempotência/deduplicação** nos webhooks — reconexão da Evolution duplica mensagens
  (gap 06-3 em [06-n8n-workflow.md](06-n8n-workflow.md)).
- Máquina de estados de chat é a única guarda de integridade de status
  (`STATUS_TRANSITIONS`). Qualquer `update` que contorne `ChatService` quebra o invariante —
  ver gap 05-7 em [05-ai-pipeline.md](05-ai-pipeline.md).
- RAG indisponível deve falhar ruidosamente, nunca "sem solução" (gap 05-6).

## Performance

- Frontend: polling de **30 s** em listas (`refetchInterval`) além do WebSocket.
- RAG: um vetor por artigo, `VECTOR_SIZE=768`, distância cosine, **sem score threshold**
  (gap 05-5). Aumento do corpus pode exigir recall/limit explícitos.
- LLM: Ollama local por padrão; latência dominada pelo provider.

## Localização e idioma

- Interface e prompts em **pt-BR**. `ia_name` configurável (default `EMSoft IA`).

## Testes (existência)

- `backend/tests/`: 8 suítes — `test_api`, `test_appwrite_schema`, `test_chat_service`,
  `test_config`, `test_cors`, `test_schemas`, `test_security`, `test_webhooks`, além de
  `conftest.py`. Estratégia detalhada em [10-test-strategy.md](10-test-strategy.md).

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 08-1 | `CORS_ORIGINS` default só `localhost:3000`; produção exige lista real e restrita | `config.py:39` | **Alta** | **ABERTO** → [09-infra-deploy](09-infra-deploy.md) |
| 08-2 | Comportamento de `verify_webhook` com `WEBHOOK_SECRET=None` em produção não está fixado por spec (aceitar vs rejeitar) | `routes/webhooks.py`, `config.py:18` | **Alta** | **ABERTO** → [03-api-contract](03-api-contract.md) |
| 08-3 | `/health` não checa dependências; liveness sem readiness | `main.py:90` | Média | **ABERTO** |
| 08-4 | Sem rate limiting em `/auth/login` e webhooks; exposição a força bruta / flood | rotas `auth`, `webhooks` | **Alta** | **ABERTO** |
| 08-5 | Sem logging estruturado nem request-id; dificuldade de correlacionar um chamado ponta a ponta | `app/**/*.py` | Média | **ABERTO** |
| 08-6 | Sem métricas/tracing/APM; nenhum SLO observável | `app/**/*.py` | Média | **ABERTO** |
| 08-7 | `DATABASE_URL` default com credenciais em claro no código | `config.py:10` | Baixa | **ABERTO** |
| 08-8 | WebSocket aceita token por query string (exposto em proxy) | `main.py:74`, `use-chat-socket.ts` | **Alta** | **ABERTO** → [07-frontend](07-frontend.md) 07-1 |

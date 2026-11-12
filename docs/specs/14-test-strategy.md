# SPEC 14 — Estratégia de testes

Cobertura atual, estratégia-alvo e gates de CI. Infraestrutura/deploy em
[09-infra-deploy.md](09-infra-deploy.md); requisitos não funcionais em
[08-non-functional.md](08-non-functional.md).

## Decisão arquitetural

- **Backend**: unitários com **fakes em memória** — `FakeStore`/`FakeRepositories` em
  `tests/conftest.py` espelham a interface dos repositórios Appwrite, injetados via
  `app.dependency_overrides[get_repositories]`. As rotas rodam em `httpx.AsyncClient`
  sobre `ASGITransport` (sem servidor), com `asyncio_mode=auto`.
- **LLM/RAG**: os testes **stubam `get_llm`/`get_embedder`** (monkeypatch) devolvendo JSON
  e vetores determinísticos, exercitando RAG → parsing → decisão de cenário sem chamar
  Ollama (`tests/test_ai_pipeline.py`) — ver gap **14-2**.
- **Frontend**: alvo Vitest (unit) + Playwright (e2e do fluxo de chamado). Hoje **não há**
  infraestrutura de teste — ver gap **14-6**.

## Cobertura atual (backend, ~1259 linhas)

| Suite | Linhas | O que cobre |
|---|---|---|
| `test_ai_pipeline.py` | 302 | `AIPipelineService` com `get_llm`/`get_embedder` stubados: cenários A/B/C, RAG sem hit, 409/502/503, auth |
| `test_api.py` | 295 | CRUD via `httpx` + `ASGITransport` + `FakeRepositories`; RBAC de cliente/prioridade/assinar |
| `test_appwrite_schema.py` | 121 | `ensure_appwrite_schema`: 9 collections, atributos, idempotência (via `FakeDatabases`) |
| `test_webhooks.py` | 130 | Auth `X-Webhook-Secret`; **fail-closed** sem segredo; payload bruto Evolution; dedup por `whatsapp_message_id` |
| `test_schemas.py` | 93 | Schemas Pydantic |
| `test_chat_service.py` | 88 | Máquina de estados `STATUS_TRANSITIONS`/`ChatService`: transições válidas/inválidas, ciclo completo, `RESOLVIDO → IA_ANALISANDO` |
| `test_config.py` | 25 | Validação de config (segredos em produção) |
| `test_cors.py` | 15 | CORS |
| `test_security.py` | 11 | JWT access/refresh: claims `typ` e `sub` |
| `conftest.py` | 179 | `FakeStore`, `FakeRepositories`, fixtures de tokens (admin/supervisor/atendente), `webhook_secret` autouse |

Cobre bem a camada de **dados/segurança** (Appwrite schema, RBAC, JWT, auth de webhook,
máquina de estados) e, parcialmente, o **pipeline de IA e o webhook de mensagem**.
Faltam a camada de **classificação de intenção/roteamento** e as **integrações externas**.

## O que não é testado

- **Router/caches de IA** — `ai/router.py` (`/ai/classificar`, `/ai/analisar`),
  `ai_cache.py` e os clients `ollama_service.py`/`openai_service.py`: sem teste unitário
  direto (o `AIPipelineService` é coberto).
- **RAG** — `qdrant_service.py` (`search_similar`, `upsert_article`, `ensure_collection`,
  dimensão 768, `article_point_id`): sem teste unitário (falha de RAG já é coberta via 503).
- **Classificação de intenção e roteamento** — separação categoria ERP × departamento e
  regras determinísticas ainda não existem no código, logo não têm teste.
- **Webhook de mensagem** — normalização, deduplicação e gravação de `ia_diagnosticos` já
  cobertas; persistência real em Appwrite não.
- **n8n** — nenhum harness valida o JSON ativo.
- **Frontend** — sem `test` script, sem specs.
- **Integração Emsoft/outbox** — não existem; serão cobertos por contract tests com mock.
- **Integração real** — Appwrite/Qdrant/Evolution só aparecem em fakes; divergências só
  emergem em deploy.

## Gates de CI (atual)

`.github/workflows/ci.yml`:

- Backend — `uv lock --check`, `ruff check app tests` (bloqueante),
  `mypy app/ --ignore-missing-imports` (bloqueante),
  `pytest tests/ -q --cov=app --cov-report=term-missing --cov-fail-under=86` (bloqueante).
- Frontend — `npm run lint` (bloqueante), `npm run test` (Vitest, bloqueante),
  `npm run build` (bloqueante).
- Docker — `build` das imagens (push desativado).

Cobertura com piso `--cov-fail-under=86`, fixado em `[tool.coverage.report]`
(`backend/pyproject.toml`) — valor medido em 2026-11-12 (450 testes), não meta aspiracional.
mypy, lint e testes do frontend agora são bloqueantes: regressões em `ai/router.py`, caches
e clients impedem merge. Gaps **09-14** e **14-9** — **CORRIGIDO**.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 14-1 | `AIPipelineService` é coberto, mas `ai/router.py`, `ai_cache.py`, `ollama_service.py` e `openai_service.py` não têm teste unitário direto | `app/ai/`; `tests/` | **Alta** | **CORRIGIDO** — `tests/test_ai_router.py` (4 endpoints com dependências mockadas: 200/404/422/502), `tests/test_ai_cache.py` (hit/miss/TTL/`clear`/fail-safe) e `tests/test_llm_services.py` (Ollama e OpenAI com `httpx.MockTransport`, sem rede) |
| 14-2 | Stub de LLM/embedder via monkeypatch de `get_llm`/`get_embedder` permite exercitar RAG → cenário de forma determinística | `tests/test_ai_pipeline.py` | **Crítica** | **CORRIGIDO** |
| 14-3 | `qdrant_service.py` sem teste unitário: `search_similar`/`upsert`/`ensure_collection`, dimensão 768, `article_point_id` | `services/qdrant_service.py` | **Alta** | **CORRIGIDO** — `tests/test_qdrant_service.py` (cliente fake, sem rede: `search_similar` com/sem filtro de categoria, `upsert_article`, `ensure_collection`, `article_point_id` e dimensão 768) → 05-6 |
| 14-4 | Render de prompt com conteúdo dinâmico não quebra mais (constantes + f-string) e o veredito é validado por Pydantic | `ai/prompts.py`; `ai_pipeline.py` | **Alta** | **CORRIGIDO** → 05-16 |
| 14-5 | Webhook de mensagem coberto ponta a ponta: payload bruto Evolution, tipos/caption e dedup por `whatsapp_message_id` | `tests/test_webhooks.py` | **Alta** | **CORRIGIDO** → 06-3 |
| 14-6 | Frontend sem infraestrutura de teste (sem `test` script, sem Vitest/Playwright) | `frontend/package.json` | **Alta** | **ABERTO (parcial)** — Vitest + jsdom + Testing Library em `vitest.config.ts` (Task F4.1); bloqueio de CI e cobertura mínima na Task R2.3 |
| 14-7 | n8n sem harness de teste; JSON ativo sem validação automatizada de nós/env | `infra/n8n/`; `backend/tests/test_workflow_n8n.py` | Média | **CORRIGIDO** — `tests/test_workflow_n8n.py` valida nós essenciais, `$env.*` × `.env.example`/compose, `onError`, path do webhook e conexões sem nó órfão → 06-11 |
| 14-8 | Sem testes de integração reais (Appwrite/Qdrant/Evolution/Emsoft); tudo em fakes | `tests/` | Média | **ABERTO** |
| 14-9 | CI sem threshold de cobertura; mypy e lint frontend report-only — regressões em IA não bloqueiam merge | `ci.yml` | Média | **CORRIGIDO** — CI 100% bloqueante: `ruff`, `mypy`, `pytest --cov-fail-under=86`, `npm run lint`, `npm run test`; `fail_under = 86` (medido) em `pyproject.toml` |
| 14-10 | Sem teste que garanta a dimensão de embedding (768 vs 1536); o bloqueio OpenAI (ADR-0005) não é travado por teste | `services/qdrant_service.py`; `ai/provider.py` | **Alta** | **CORRIGIDO** — `tests/test_qdrant_dimensao.py` trava `VECTOR_SIZE == 768`, a criação da coleção com 768/COSINE (cliente fake, sem rede) e o `get_embedder()` sempre retornando Ollama mesmo com provider OpenAI (ADR-0005) |
| 14-11 | Sem testes de classificação de intenção, separação categoria ERP × departamento e resolução de roteamento | `app/ai/`; `app/services/` | **Alta** | **CORRIGIDO** — `tests/data/intencao_rotulada.py` + `test_intencao_regressao.py` |
| 14-12 | Sem contract tests do adapter Emsoft e do ciclo outbox/reprocessamento | `app/integrations/` | **Alta** | **ABERTO (parcial)** — adapter Emsoft coberto por 18 testes (`tests/test_integracao_emsoft_chamados.py`: validação de contrato, ciclo criar/editar, reconciliação, retry e rotas); ciclo outbox/reprocessamento ainda sem testes → 12 |

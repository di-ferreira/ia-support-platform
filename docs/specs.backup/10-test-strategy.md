# SPEC 10 — Estratégia de testes

Cobertura atual, estratégia-alvo e gates de CI. Infraestrutura/deploy em
[09-infra-deploy.md](09-infra-deploy.md); requisitos não funcionais em
[08-non-functional.md](08-non-functional.md).

## Decisão arquitetural

- **Backend**: unitários com **fakes em memória** — `FakeStore`/`FakeRepositories` em
  `tests/conftest.py` espelham a interface dos repositórios Appwrite, injetados via
  `app.dependency_overrides[get_repositories]`. As rotas rodam em `httpx.AsyncClient`
  sobre `ASGITransport` (sem servidor), com `asyncio_mode=auto`.
- **LLM/RAG**: a estratégia-alvo é um **stub de LLM** (`llm.embed`/`chat`) que devolve
  vetores e JSON estruturados determinísticos, permitindo testar o pipeline
  RAG → parsing → decisão de cenário sem chamar Ollama. **Esse stub ainda não existe** —
  ver gap **10-2**.
- **Frontend**: alvo Vitest (unit) + Playwright (e2e do fluxo de chamado). Hoje **não há**
  infraestrutura de teste — ver gap **10-6**.

## Cobertura atual (backend, 847 linhas)

| Suite | Linhas | O que cobre |
|---|---|---|
| `test_api.py` | 275 | CRUD via `httpx` + `ASGITransport` + `FakeRepositories` |
| `test_appwrite_schema.py` | 121 | `ensure_appwrite_schema`: 9 collections, atributos, idempotência (via `FakeDatabases`) |
| `test_chat_service.py` | 69 | Máquina de estados `STATUS_TRANSITIONS`/`ChatService`: transições válidas/inválidas, ciclo completo |
| `test_schemas.py` | 93 | Schemas Pydantic |
| `test_webhooks.py` | 59 | Auth por `X-Webhook-Secret`; **fail-closed** com `webhook_secret=None` (monkeypatch) |
| `test_config.py` | 25 | Validação de config |
| `test_cors.py` | 15 | CORS |
| `test_security.py` | 11 | JWT access/refresh: claims `typ` e `sub` |
| `conftest.py` | 179 | `FakeStore`, `FakeRepositories`, fixtures de tokens (admin/supervisor/atendente), `webhook_secret` autouse |

Cobre bem a camada de **dados/segurança** (Appwrite schema, RBAC, JWT, auth de webhook,
máquina de estados). A camada de **IA está fora de qualquer suite**.

## O que não é testado

- **Pipeline de IA** — `/ai/classificar`, `/ai/analisar`, `/ai/solucionar`: zero testes.
- **RAG** — `qdrant_service.py` (`search_similar`, `upsert_article`, `ensure_collection`,
  dimensão 768, fallback Cenário C): sem teste.
- **Decisão de cenário A/B/C** e **render de prompt** (`prompts.py:75` `.format` —
  gap 05-16): sem teste.
- **Stub de LLM** — `llm.embed`/`llm.chat` nunca são simulados nos testes.
- **Webhook de mensagem** — só a auth é testada; normalização, deduplicação e gravação em
  `ia_diagnosticos` não são.
- **n8n** — nenhum harness valida o JSON ativo.
- **Frontend** — sem `test` script, sem specs.
- **Integração real** — Appwrite/Qdrant/Evolution só aparecem em fakes; divergências só
  emergem em deploy.

## Gates de CI (atual)

`.github/workflows/ci.yml`:

- Backend — `uv lock --check`, `ruff check app tests` (bloqueante),
  `mypy app/ --ignore-missing-imports || true` (**report-only**), `pytest tests/ -q`.
- Frontend — `npm run lint || true` (**report-only**), `npm run build` (bloqueante).
- Docker — `build` das imagens (push desativado).

Sem threshold de cobertura; mypy e lint do frontend não bloqueiam. Como não há teste de IA,
uma regressão no pipeline **não** impede merge. Ver gaps **09-14** e **10-9**.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 10-1 | Pipeline de IA (`/ai/*`, RAG, decisão A/B/C) **sem nenhum teste** — contraria o argumento de "testável" do ADR-0004 | `app/ai/router.py`; `tests/` | **Crítica** | **ABERTO** |
| 10-2 | Sem **stub de LLM** (`llm.embed`/`chat`); impossível exercitar RAG → cenário de forma determinística | `tests/conftest.py` | **Crítica** | **ABERTO** |
| 10-3 | `qdrant_service.py` sem teste: `search_similar`/`upsert`/`ensure_collection`, dimensão 768, fallback Cenário C | `services/qdrant_service.py` | **Alta** | **ABERTO** → 05-6 |
| 10-4 | Render de prompt via `.format` não testado; chaves `{}` de artigo quebram | `ai/prompts.py:75` | **Alta** | **ABERTO** → 05-16 |
| 10-5 | Webhook de mensagem não testado de ponta a ponta (normalização, dedup, `ia_diagnosticos`); só a auth | `tests/test_webhooks.py` | **Alta** | **ABERTO** → 06-3 |
| 10-6 | Frontend sem infraestrutura de teste (sem `test` script, sem Vitest/Playwright) | `frontend/package.json` | **Alta** | **ABERTO** |
| 10-7 | n8n sem harness de teste; JSON ativo sem validação de nós/env | `infra/n8n/` | Média | **ABERTO** → 06-11 |
| 10-8 | Sem testes de integração reais (Appwrite/Qdrant/Evolution); tudo em fakes | `tests/` | Média | **ABERTO** |
| 10-9 | CI sem threshold de cobertura; mypy e lint frontend report-only — regressão de IA não bloqueia merge | `ci.yml` | Média | **ABERTO** → 09-14 |
| 10-10 | Sem teste que garanta a dimensão de embedding (768 vs 1536); o bloqueio OpenAI (ADR-0005) não é travado por teste | `services/qdrant_service.py`; `openai_service.py` | **Alta** | **ABERTO** → 05-11, ADR-0005 |

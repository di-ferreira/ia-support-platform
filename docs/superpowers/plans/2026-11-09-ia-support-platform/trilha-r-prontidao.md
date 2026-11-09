# Trilha R — Prontidão Operacional

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os gaps que impedem a plataforma de rodar em produção com evidência — pilha prod completa (Appwrite/Ollama), health de prontidão, logging correlacionável, métricas de produto com semântica correta e CI que bloqueia regressão — sem tocar no contrato Emsoft e sem reescrever o produto.

**Architecture:** A trilha é cortada em três blocos por **dependência real**, não por conveniência:

- **R0 — pré-rollout** (5 tasks): a pilha de produção passa a conter as dependências que o código já assume. Nada de feature nova; o objetivo é `docker compose -f infra/docker-compose.prod.yml up -d` subir um backend que responde `/health/ready` = 200, e `start-prod.sh` só declarar sucesso depois disso.
- **R1 — observabilidade e métricas** (4 tasks): logging estruturado com correlation id, `tempo_medio_resposta` com semântica correta, métricas de produto (resolução confirmada, transbordo, duplicidade, por departamento) e health degradado do bootstrap. É o bloco que **torna a meta de 70% mensurável** — por isso roda antes da Fase 4.
- **R2 — duração** (6 tasks): CI bloqueante com cobertura mínima (o harness Vitest já nasceu na F4.1), backup agendado de Appwrite/Qdrant/n8n, fim do drift Alembic/Postgres, credenciais fora do compose.

**Tech Stack:** Docker Compose v2, Traefik, Appwrite (self-hosted), Qdrant, Ollama, Postgres 16, Redis 7, Evolution API, n8n; FastAPI + Pydantic Settings + `httpx` para as sondas de saúde; `logging` + middleware ASGI para correlação; pytest + PyYAML para os testes de contrato de infraestrutura; GitHub Actions (Node 22 / Python 3.11→3.12); Vitest 2 (harness da F4.1) + `@vitest/coverage-v8`.

**Specs:** `docs/specs/08-non-functional.md` (Gaps 08-1, 08-3, 08-5, 08-6, 08-7, 08-9, 08-12), `docs/specs/09-infra-deploy.md` (Gaps 09-1…09-9, 09-14, 09-15, 09-16), `docs/specs/00-escopo.md` (metas de 70% e indicadores), `docs/specs/02-data-model.md` (Gaps 02-10, 02-11, 02-14), `docs/specs/12-confiabilidade-integracoes.md` (Gap 12-6), `docs/specs/14-test-strategy.md` (Gaps 14-6, 14-9), `docs/specs/07-frontend.md` (testes de UI).

## Global Constraints

Vale `README.md` §Global Constraints (C1–C12). Em especial:

- **C1** — toda task começa pelo teste que falha. Para infraestrutura, o "teste" é um teste Python que **lê e valida** o arquivo (`docker-compose.prod.yml`, `start-prod.sh`, `ci.yml`, `.env.example`): sem isso a task vira edição de YAML sem verificação.
- **C2** — verificação real. Tasks só de infraestrutura rodam `pytest tests/ -q && ruff check app tests`; tasks de backend somam o teste específico; a R2.1/R2.2/R2.3 rodam o pipeline local equivalente (`uv run pytest --cov`, `npm run test`).
- **C4** — gap fechado muda a linha do Registro de Gaps na mesma task.
- **C5** — `EMSOFT_CHAMADOS_ENABLED` continua `false`; nenhuma task desta trilha cria cliente Emsoft. A R0 **não** adiciona variáveis `EMSOFT_CHAMADOS_*` (isso pertence ao gap 09-17, bloqueado por 11-1).
- **C9** — nenhum segredo real no repositório: `.env.example` recebe chaves vazias ou placeholders explícitos (`troque-este-valor`), nunca valores de produção.
- **C12** — nenhum teste desta trilha exige Docker, Appwrite, Qdrant ou Ollama rodando: os contratos de infraestrutura são validados por leitura de arquivo e as sondas por injeção de dependência.

**Gate de entrada:** R0 não tem pré-requisito (pode começar junto da F1). R1 exige **G3** (Fases 1–3 concluídas), porque `tempo_medio_resposta` e métricas por departamento consultam `chats.departamento_id` e o escopo de `obter_dashboard(user=...)` criado na F1.9. R2 exige **G4**.

## Rastreio gap → task

| Gap | Task | Evidência que fecha |
|---|---|---|
| 08-1 | R0.1 | produção recusa `CORS_ORIGINS` localhost/default |
| 08-3 | R0.2 | `GET /health/ready` com sondas reais e 503 quando degradado |
| 09-1, 09-4 | R0.3 | serviço `appwrite` no compose prod + rede compartilhada com o backend |
| 09-2 | R0.3, R0.5 | bloco de env completo no compose e paridade `Settings` ↔ `.env.example` |
| 09-15 | R0.3 | serviço `ollama` + `OLLAMA_BASE_URL` no backend prod |
| 09-16 | R0.4 | `start-prod.sh` espera healthcheck real e não roda Alembic |
| 05-14 | R0.5 | modelo Ollama idêntico em `config.py` e `.env.example` |
| 08-5, 12-6 | R1.1 | log JSON com `request_id`, `chat_id` e `event` em toda requisição |
| 00-10 | R1.2 | `tempo_medio_resposta` = tempo até a **primeira** resposta humana de cada chat |
| 08-9, 00-16 | R1.3 | `GET /dashboard/metricas` com resolução confirmada, transbordo, duplicidade e recorte por departamento |
| 08-12 | R1.4 | falha de bootstrap vira estado explícito em `/health/ready` e no log |
| 09-9 | R2.1 | Python 3.11 único em `pyproject`/`Dockerfile`/CI |
| 05-19 | R2.1 | dependência `openai` removida (o provider usa `httpx`) |
| 09-14, 14-9 | R2.2, R2.3 | `mypy`, lint, testes e cobertura bloqueiam o merge |
| 14-6 | R2.3 | Vitest roda no CI com threshold (harness criado na F4.1) |
| 09-5, 09-6, 09-7, 00-7 | R2.4 | backup de Appwrite/Qdrant/n8n/evolution com agendamento versionado |
| 02-11, 02-14 | R2.5 | ORM/Alembic legado removidos; `seed_qdrant.py` lê do Appwrite |
| 09-8, 08-7, 09-3 | R2.6 | senhas vindas do env; MinIO órfão removido; `DATABASE_URL` sem default com credencial |

**Fora da trilha R:** 09-17/09-18 (worker Emsoft e runbook de rollout) dependem do contrato (11-1); 08-10/08-11 (degradação e retry de integrações) são do bloco 12 e também exigem 11-1; 14-8/14-10 dependem de serviços reais ou de decisão de embedding (ADR-0005 já fechou o lado da dimensão).

---

## R0 — Pré-rollout

### Task R0.1: `CORS_ORIGINS` seguro em produção

**Files:**
- Modify: `backend/app/core/config.py:39` (`cors_origins` + `validate_production_secrets`)
- Test: `backend/tests/test_config_producao.py`

**Interfaces:**
- Produces: `Settings.validate_production_secrets()` também recusa origem `http://localhost*` / `http://127.0.0.1*` quando `environment == "production"`; `Settings.cors_origins` permanece `list[str]` (parse JSON do env, como o pydantic-settings já faz).

**Regra:** o default de desenvolvimento (`http://localhost:3000`) continua válido em `development`; em produção a lista tem de ser explícita e sem localhost. Fail-closed: lista vazia em produção também é recusada (CORS sem origem permitida é melhor que CORS aberto, mas o operador precisa saber que errou).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_config_producao.py`:

```python
"""Configuracao de producao nao aceita defaults de desenvolvimento."""

import pytest

from app.core.config import Settings

_SEGREDO = "chave-forte-de-producao"
_WEBHOOK = "segredo-de-webhook"


def _producao(**extra) -> Settings:
    base = {
        "environment": "production",
        "secret_key": _SEGREDO,
        "webhook_secret": _WEBHOOK,
        "cors_origins": ["https://app.emsoft.app"],
    }
    base.update(extra)
    return Settings(_env_file=None, **base)


def test_producao_com_origem_https_passa():
    _producao().validate_production_secrets()


def test_producao_recusa_origem_localhost():
    config = _producao(cors_origins=["http://localhost:3000"])

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        config.validate_production_secrets()


def test_producao_recusa_lista_vazia():
    config = _producao(cors_origins=[])

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        config.validate_production_secrets()


def test_producao_recusa_127_0_0_1():
    config = _producao(cors_origins=["https://app.emsoft.app", "http://127.0.0.1:3000"])

    with pytest.raises(ValueError, match="127.0.0.1"):
        config.validate_production_secrets()


def test_desenvolvimento_aceita_localhost():
    config = Settings(_env_file=None, environment="development")

    config.validate_production_secrets()  # nao levanta

    assert config.cors_origins == ["http://localhost:3000"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_producao.py -v`

Expected: FAIL — `test_producao_recusa_origem_localhost`, `test_producao_recusa_lista_vazia` e `test_producao_recusa_127_0_0_1` não levantam `ValueError`.

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/core/config.py`, ao final de `validate_production_secrets`:

```python
        if not self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS vazio; defina as origens do frontend em produção"
            )
        for origem in self.cors_origins:
            if "localhost" in origem or "127.0.0.1" in origem:
                raise ValueError(
                    f"CORS_ORIGINS contém origem de desenvolvimento ({origem}); "
                    "use apenas os domínios públicos em produção"
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config_producao.py -v`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_config_producao.py
git commit -m "feat(config): producao recusa cors de desenvolvimento

- CORS_ORIGINS vazio ou com localhost falha antes do app subir
- default de desenvolvimento preservado"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 08)**

```
| 08-1 | `CORS_ORIGINS` default só `localhost:3000` | `core/config.py:39` | **Alta** | **CORRIGIDO** — produção exige lista explícita sem localhost (`validate_production_secrets`, teste em `tests/test_config_producao.py`) |
```

---

### Task R0.2: `GET /health/ready` com sondas de dependência

**Files:**
- Create: `backend/app/services/health_service.py`
- Modify: `backend/app/main.py:88-92` (rota `/health`, nova `/health/ready`)
- Test: `backend/tests/test_health_ready.py`

**Interfaces:**
- Produces:
  - `Sonda = Callable[[], Awaitable[None]]` — retorna normalmente = ok; levanta = falha
  - `HealthService(sondas: dict[str, Sonda], timeout: float = 2.0)`
  - `HealthService.pronto() -> dict` → `{"status": "ok" | "degradado", "checks": {nome: {"ok": bool, "erro": str | None}}}`
  - `GET /health/ready` → 200 quando `status == "ok"`, **503** quando degradado; corpo igual ao de `pronto()`
  - `GET /health` continua respondendo `{"status": "ok"}` (liveness, sem dependências)

**Regras:** cada sonda roda com `asyncio.wait_for(timeout)`, em paralelo (`asyncio.gather`); uma sonda que estoura não impede as outras de reportar. A mensagem de erro é **sanitizada**: só o tipo da exceção e um texto curto, nunca URL com credencial ou corpo de resposta. Se `app.state.saude` não existir (testes, boot parcial), a rota responde 503 `{"status": "degradado", "checks": {"servico": {"ok": false, "erro": "nao inicializado"}}}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_health_ready.py`:

```python
"""Readiness separa liveness de dependencias reais."""

import asyncio

import pytest

from app.main import app
from app.services.health_service import HealthService


async def _ok() -> None:
    return None


async def _falha() -> None:
    raise RuntimeError("qdrant fora do ar")


async def _lenta() -> None:
    await asyncio.sleep(5)


@pytest.mark.asyncio
async def test_tudo_ok_retorna_status_ok():
    saude = HealthService({"appwrite": _ok, "qdrant": _ok}, timeout=0.5)

    resultado = await saude.pronto()

    assert resultado["status"] == "ok"
    assert resultado["checks"]["appwrite"] == {"ok": True, "erro": None}


@pytest.mark.asyncio
async def test_uma_falha_degrada_sem_esconder_as_outras():
    saude = HealthService({"appwrite": _ok, "qdrant": _falha}, timeout=0.5)

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["appwrite"]["ok"] is True
    assert resultado["checks"]["qdrant"]["ok"] is False
    assert "qdrant fora do ar" in resultado["checks"]["qdrant"]["erro"]


@pytest.mark.asyncio
async def test_sonda_lenta_estoura_no_timeout():
    saude = HealthService({"ollama": _lenta}, timeout=0.05)

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["ollama"]["ok"] is False
    assert "Timeout" in resultado["checks"]["ollama"]["erro"] or (
        "timeout" in resultado["checks"]["ollama"]["erro"].lower()
    )


@pytest.mark.asyncio
async def test_rota_ready_responde_200_quando_pronto(client):
    app.state.saude = HealthService({"appwrite": _ok}, timeout=0.5)

    resp = await client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_rota_ready_responde_503_quando_degradado(client):
    app.state.saude = HealthService({"qdrant": _falha}, timeout=0.5)

    resp = await client.get("/health/ready")

    assert resp.status_code == 503
    assert resp.json()["checks"]["qdrant"]["ok"] is False


@pytest.mark.asyncio
async def test_health_simples_nao_depende_de_sonda(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_health_ready.py -v`

Expected: FAIL — `ModuleNotFoundError: app.services.health_service` e 404 em `/health/ready`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/services/health_service.py`:

```python
"""Sondas de prontidao (readiness) separadas do liveness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

Sonda = Callable[[], Awaitable[None]]


class HealthService:
    def __init__(self, sondas: dict[str, Sonda], timeout: float = 2.0) -> None:
        self._sondas = sondas
        self._timeout = timeout

    async def _executar(self, sonda: Sonda) -> dict:
        try:
            await asyncio.wait_for(sonda(), timeout=self._timeout)
            return {"ok": True, "erro": None}
        except asyncio.TimeoutError:
            return {"ok": False, "erro": f"timeout de {self._timeout}s"}
        except Exception as exc:  # noqa: BLE001 - readiness nunca derruba a rota
            return {"ok": False, "erro": f"{type(exc).__name__}: {exc}"[:200]}

    async def pronto(self) -> dict:
        nomes = list(self._sondas)
        resultados = await asyncio.gather(
            *(self._executar(self._sondas[nome]) for nome in nomes)
        )
        checks = dict(zip(nomes, resultados, strict=True))
        status = "ok" if all(c["ok"] for c in checks.values()) else "degradado"
        return {"status": status, "checks": checks}
```

Em `backend/app/main.py`, substituir a rota de health e importar o que falta (`from fastapi import Request, status`, `from fastapi.responses import JSONResponse`, `from app.services.health_service import HealthService`):

```python
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(request: Request):
    saude: HealthService | None = getattr(request.app.state, "saude", None)
    if saude is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degradado",
                "checks": {"servico": {"ok": False, "erro": "nao inicializado"}},
            },
        )
    resultado = await saude.pronto()
    return JSONResponse(
        status_code=(
            status.HTTP_200_OK
            if resultado["status"] == "ok"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content=resultado,
    )
```

Ainda em `main.py`, no `lifespan`, montar as sondas com o que já existe (a ligação de `schema` entra na R1.4):

```python
    app.state.saude = build_health_service(app.state.appwrite_databases)
```

e criar `backend/app/services/health_service.py` → `build_health_service(databases) -> HealthService` no mesmo arquivo:

```python
def build_health_service(databases) -> HealthService:
    async def appwrite_ok() -> None:
        databases.list()

    return HealthService({"appwrite": appwrite_ok})
```

(A sonda de `schema` entra na R1.4, junto do health degradado do bootstrap — aqui o readiness reporta só o que o boot já toca de forma síncrona. Qdrant e Ollama ficam fora do readiness de propósito.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_health_ready.py -v`

Expected: PASS (6 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/health_service.py backend/app/main.py backend/tests/test_health_ready.py
git commit -m "feat(health): readiness com sondas de dependencia

- /health continua liveness puro; /health/ready responde 503 se degradado
- sondas rodam em paralelo com timeout e erro sanitizado
- boot parcial (sem servico de saude) tambem responde 503"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 08)**

```
| 08-3 | `/health` não checa dependências; sem readiness | `main.py:90-92` | Média | **CORRIGIDO** — `GET /health/ready` com `HealthService` (sondas paralelas, timeout, 503 degradado) em `services/health_service.py` |
```

---

### Task R0.3: Compose de produção com Appwrite, Ollama e env completo

**Files:**
- Modify: `infra/docker-compose.prod.yml` (bloco `backend`, novo serviço `ollama`, rede `appwrite`, healthcheck — `qdrant` já existe e só ganha a URL interna no env)
- Modify: `backend/pyproject.toml` e `backend/requirements.txt` (declarar `pyyaml` — o teste lê o compose)
- Test: `backend/tests/test_compose_prod.py`

**Interfaces:**
- Produces: `docker compose -f infra/docker-compose.prod.yml config` válido com
  - rede `appwrite` declarada como **externa** (`name: appwrite`), compartilhada entre `backend` e a pilha de `infra/appwrite/`;
  - `backend.environment` com `APPWRITE_ENDPOINT=http://appwrite/v1`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, `SECRET_KEY`, `WEBHOOK_SECRET`, `CORS_ORIGINS`, `QDRANT_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`;
  - serviço `ollama` com volume e healthcheck;
  - `backend.healthcheck` batendo em `/health/ready` (Task R0.2).

**Decisão de rede:** a pilha do Appwrite já fixa nomes de rede (`name: appwrite`, `name: gateway`). Em vez de embutir 25 serviços no compose prod (e duplicar o Traefik, que colidiria em 80/443), o compose prod **entra** na rede `appwrite` como externa e `scripts/start-prod.sh` sobe a pilha do Appwrite antes do backend (Task R0.4). Consequência operacional: `docker network create appwrite` deixa de ser necessário — a pilha do Appwrite cria a rede ao subir.

**Regra:** nenhuma credencial real no arquivo — todo valor sensível vem de `${VAR}` (C9). `EMSOFT_CHAMADOS_*` **não** entra aqui (C5, gap 09-17 bloqueado).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_compose_prod.py`:

```python
"""Contrato da pilha de producao, validado sem docker."""

from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load(
    (RAIZ / "infra/docker-compose.prod.yml").read_text(encoding="utf-8")
)


def _servico(nome: str) -> dict:
    return COMPOSE["services"][nome]


def _env(nome: str) -> dict:
    return _servico(nome)["environment"]


def test_backend_alcanca_appwrite_pela_rede_compartilhada():
    assert _env("backend")["APPWRITE_ENDPOINT"] == "http://appwrite/v1"
    assert "appwrite" in _servico("backend")["networks"]
    assert COMPOSE["networks"]["appwrite"]["external"] is True
    assert COMPOSE["networks"]["appwrite"]["name"] == "appwrite"


def test_backend_recebe_credenciais_e_origens_do_env():
    env = _env("backend")

    for chave in ("SECRET_KEY", "WEBHOOK_SECRET", "CORS_ORIGINS", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        assert env[chave] == f"${{{chave}}}", f"{chave} deve vir do env, nunca literal"


def test_backend_aponta_para_qdrant_e_ollama_da_rede():
    env = _env("backend")

    assert env["QDRANT_URL"] == "http://qdrant:6333"
    assert env["OLLAMA_BASE_URL"] == "http://ollama:11434"
    assert env["OLLAMA_MODEL"] == "${OLLAMA_MODEL}"


def test_ollama_existe_com_volume_e_healthcheck():
    ollama = _servico("ollama")

    assert any("qdrant" not in v and "ollama" in v for v in ollama["volumes"])
    assert "healthcheck" in ollama
    assert ollama["restart"] == "unless-stopped"


def test_backend_tem_healthcheck_de_readiness():
    healthcheck = _servico("backend")["healthcheck"]

    assert "health/ready" in " ".join(healthcheck["test"])
    assert healthcheck["retries"] >= 3


def test_backend_nao_depende_de_postgres_para_subir():
    """Appwrite e a store primaria; Postgres fica apenas para Evolution/n8n."""
    depends = _servico("backend").get("depends_on", {})

    assert "appwrite" not in depends or depends["appwrite"]["condition"] == "service_healthy"
    assert "postgres" not in depends
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_compose_prod.py -v`

Expected: FAIL — `KeyError: 'appwrite'` em `COMPOSE["networks"]` e `APPWRITE_ENDPOINT` ausente do env do backend.

- [ ] **Step 3: Write minimal implementation**

Primeiro, declare a dependência que o teste usa (não confie em dependência transitiva). O projeto usa `[project.optional-dependencies] dev` (não `[dependency-groups]`), então edite à mão:

```toml
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
    "aiosqlite>=0.20.0",
    "pyyaml>=6.0",
]
```

e acrescente `pyyaml>=6.0` a `backend/requirements.txt`. Depois:

```bash
cd backend && uv lock && uv sync --frozen --extra dev
```

Em `infra/docker-compose.prod.yml`, substituir o bloco `backend` e acrescentar `ollama` + redes:

```yaml
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    environment:
      ENVIRONMENT: production
      SECRET_KEY: ${SECRET_KEY}
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      CORS_ORIGINS: ${CORS_ORIGINS}
      APPWRITE_ENDPOINT: http://appwrite/v1
      APPWRITE_PROJECT_ID: ${APPWRITE_PROJECT_ID}
      APPWRITE_API_KEY: ${APPWRITE_API_KEY}
      QDRANT_URL: http://qdrant:6333
      OLLAMA_BASE_URL: http://ollama:11434
      OLLAMA_MODEL: ${OLLAMA_MODEL}
      OLLAMA_EMBED_MODEL: ${OLLAMA_EMBED_MODEL}
      REDIS_URL: redis://redis:6379/0
      EVOLUTION_API_URL: http://evolution-api:8080
      EVOLUTION_API_KEY: ${EVOLUTION_API_KEY}
    networks:
      - default
      - appwrite
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - |
          import sys, urllib.request
          try:
              sys.exit(0 if urllib.request.urlopen("http://localhost:8000/health/ready", timeout=3).status == 200 else 1)
          except Exception:
              sys.exit(1)
      interval: 15s
      timeout: 5s
      retries: 4
      start_period: 30s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.emsoft.app`)"
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_started

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD-SHELL", "ollama list >/dev/null 2>&1 || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 20s
    restart: unless-stopped
```

Acrescentar ao final do arquivo:

```yaml
networks:
  appwrite:
    name: appwrite
    external: true
```

e ao bloco `volumes:` existente:

```yaml
  ollama-data:
```

> `DATABASE_URL_PROD` sai do env do backend: em produção a store é Appwrite (o runtime não usa PostgreSQL). Postgres permanece no compose porque Evolution API e n8n dependem dele — a remoção definitiva do drift é a Task R2.5.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_compose_prod.py -v`

Expected: PASS (6 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add infra/docker-compose.prod.yml backend/tests/test_compose_prod.py \
  backend/pyproject.toml backend/uv.lock backend/requirements.txt
git commit -m "feat(infra): compose prod com appwrite, ollama e env completo

- backend entra na rede appwrite e usa http://appwrite/v1
- ollama sobe com volume e healthcheck; qdrant/ollama viram URLs internas
- healthcheck do backend usa /health/ready (aguarda de verdade a subir)
- credenciais seguem vindo do env, nunca literais"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09 e 08)**

```
| 09-1 | Appwrite (store primária) ausente da pilha prod; backend aponta para `127.0.0.1:8020` | `infra/docker-compose.prod.yml`; `core/config.py:13` | **Crítica** | **CORRIGIDO** — backend prod entra na rede `appwrite` e usa `APPWRITE_ENDPOINT=http://appwrite/v1` (Task R0.3) |
| 09-2 | Bloco de env do backend prod incompleto | `infra/docker-compose.prod.yml` | **Crítica** | **CORRIGIDO** — `SECRET_KEY`, `WEBHOOK_SECRET`, `CORS_ORIGINS`, `APPWRITE_*`, `QDRANT_URL`, `OLLAMA_*`, `REDIS_URL` presentes (Task R0.3) |
| 09-4 | Pilha do Appwrite em rede isolada; backend prod não a alcança | `infra/appwrite/` vs `docker-compose.prod.yml` | **Alta** | **CORRIGIDO** — rede `appwrite` declarada externa e compartilhada (Task R0.3) |
| 09-15 | Sem serviço de LLM (Ollama) na pilha prod nem `OLLAMA_URL` | `infra/docker-compose.prod.yml` | **Crítica** | **CORRIGIDO** — serviço `ollama` com volume/healthcheck e `OLLAMA_BASE_URL=http://ollama:11434` (Task R0.3) |
```

---

### Task R0.4: `start-prod.sh` espera readiness real e não roda Alembic

**Files:**
- Modify: `scripts/start-prod.sh`
- Test: `backend/tests/test_start_prod_script.py`

**Interfaces:**
- Produces: `start-prod.sh` que
  1. sobe a pilha do Appwrite (`infra/appwrite/docker-compose.yml`) com as portas do Traefik dela em loopback (`_APP_HTTP_PORT=127.0.0.1:8081`, `_APP_HTTPS_PORT=127.0.0.1:8443`) para não colidir com o Traefik do compose prod;
  2. sobe o compose prod com `up -d --wait --wait-timeout 240`;
  3. confirma `/health/ready` de dentro do container do backend e **falha** (exit 1) se não estiver `ok`;
  4. baixa o modelo do Ollama se `OLLAMA_MODEL` não estiver presente (`ollama pull`);
  5. não executa `alembic upgrade head`.

**Regra:** o script termina com status ≠ 0 em qualquer falha (`set -euo pipefail` já garante para os comandos; a verificação de readiness tem `exit 1` explícito). Nada de `sleep` como sincronização — `--wait` do compose já espera `healthy`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_start_prod_script.py`:

```python
"""O script de producao precisa esperar dependencias reais."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = (RAIZ / "scripts/start-prod.sh").read_text(encoding="utf-8")


def test_nao_roda_migracao_alembic():
    assert "alembic upgrade" not in SCRIPT
    assert "sleep 5" not in SCRIPT


def test_sobe_appwrite_antes_do_backend():
    pos_appwrite = SCRIPT.index("Starting Appwrite")
    pos_backend = SCRIPT.index("Starting stack")

    assert pos_appwrite < pos_backend
    assert "appwrite/docker-compose.yml" in SCRIPT


def test_usa_wait_do_compose_em_vez_de_sleep():
    assert "--wait" in SCRIPT
    assert "--wait-timeout" in SCRIPT


def test_confirma_readiness_e_falha_quando_degradado():
    assert "health/ready" in SCRIPT
    assert "exit 1" in SCRIPT


def test_baixa_modelo_do_ollama():
    assert "ollama pull" in SCRIPT


def test_compose_recebe_o_env_file_explicitamente():
    """O compose le o `.env.prod` por `--env-file` (parser dotenv proprio).

    Assim a interpolacao `${VAR}` nao depende de o `source` ter exportado tudo,
    e valores com aspas — como `CORS_ORIGINS='["http://..."]'` — sao lidos
    corretamente pelo compose, sem uma camada extra de aspas.
    """
    assert SCRIPT.count("--env-file") >= 2
    assert '"$ENV_FILE"' in SCRIPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_start_prod_script.py -v`

Expected: FAIL — o script atual tem `sleep 5` e `alembic upgrade head`.

- [ ] **Step 3: Write minimal implementation**

Substitua `scripts/start-prod.sh` por:

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${1:-infra/.env.prod}"
COMPOSE_FILE="infra/docker-compose.prod.yml"
APPWRITE_FILE="infra/appwrite/docker-compose.yml"

echo "=== Starting EMSoft Support - Production ==="
echo "Using compose file: $COMPOSE_FILE"
echo "Using env file: $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Environment file $ENV_FILE not found."
  echo "Copy infra/.env.example to $ENV_FILE and configure it."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "Pulling latest images..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull

echo "Starting Appwrite (store primária)..."
_APP_HTTP_PORT=127.0.0.1:8081 \
_APP_HTTPS_PORT=127.0.0.1:8443 \
  docker compose -f "$APPWRITE_FILE" up -d --wait --wait-timeout 300

echo "Starting stack..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --wait --wait-timeout 240

echo "Garantindo modelo do Ollama (${OLLAMA_MODEL:-llama3.2})..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T ollama \
  ollama pull "${OLLAMA_MODEL:-llama3.2}"

echo "Verificando readiness do backend..."
if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  python -c "
import sys, urllib.request
try:
    with urllib.request.urlopen('http://localhost:8000/health/ready', timeout=5) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
"; then
  echo "Error: backend não está pronto (/health/ready != 200)."
  docker compose -f "$COMPOSE_FILE" logs --tail 50 backend
  exit 1
fi

echo "=== Deployment complete ==="
echo "Frontend: https://app.emsoft.app"
echo "Backend:  https://api.emsoft.app"
echo "n8n:      https://n8n.emsoft.app"
```

> `source "$ENV_FILE"` substitui `export $(grep ... | xargs)`, que quebra com valores que contêm espaços. Além disso, todo comando `docker compose` do compose **prod** recebe `--env-file "$ENV_FILE"`: o compose faz sua própria leitura dotenv (removendo apenas UMA camada de aspas externas), então `CORS_ORIGINS='["http://..."]'` chega ao container como JSON válido sem depender do que o shell exportou. O comando do compose do **Appwrite** não usa `--env-file` porque tem `.env` próprio em `infra/appwrite/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_start_prod_script.py -v`

Expected: PASS (6 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add scripts/start-prod.sh backend/tests/test_start_prod_script.py
git commit -m "fix(infra): start-prod espera readiness real e nao roda alembic

- sobe a pilha do Appwrite antes do backend (rede appwrite)
- compose up --wait substitui sleep como sincronizacao
- falha explicita com logs quando /health/ready != 200
- baixa o modelo do Ollama no deploy; sem migrate de PostgreSQL"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 09)**

```
| 09-16 | `start-prod.sh`: `sleep 5` em vez de aguardar healthcheck; roda Alembic | `scripts/start-prod.sh` | Baixa | **CORRIGIDO** — `docker compose up --wait` + verificação de `/health/ready` com `exit 1`; migração Alembic removida (Task R0.4) |
| 09-1 | Appwrite (store primária) ausente da pilha prod | `infra/docker-compose.prod.yml` | **Crítica** | **CORRIGIDO** — compose prod entra na rede `appwrite` (R0.3) e `start-prod.sh` sobe `infra/appwrite/docker-compose.yml` antes do backend (R0.4) |
```

---

### Task R0.5: Paridade `Settings` ↔ `.env.example` e fim do drift de modelo

**Files:**
- Modify: `infra/.env.example` (modelo Ollama, bloco de produção, `CORS_ORIGINS` como JSON entre aspas simples)
- Modify: `backend/app/core/config.py:31` (`ollama_model`)
- Test: `backend/tests/test_env_example.py`

**Interfaces:**
- Produces: `.env.example` documentando **todas** as chaves que o compose prod e o backend exigem, com placeholders explícitos; `Settings.ollama_model == "llama3.2"` idêntico ao exemplo.

**Decisão do modelo (gap 05-14):** o compose de produção passa a rodar Ollama local (R0.3), então o padrão é `llama3.2`. `.env.example` dizia `deepseek-v4-flash:cloud`, que exige Ollama Cloud/credencial e **não** existe na imagem local — o drift é fechado apontando o exemplo para o modelo que a pilha realmente baixa. Quem usa Ollama Cloud sobrescreve `OLLAMA_MODEL` no `.env.prod` (documentado no próprio arquivo).

**Regra:** o teste é de **paridade**, não de conteúdo: compara a lista de chaves exigidas com as linhas do exemplo e recusa valor preenchido para chave sensível (C9). `DATABASE_URL` sai do exemplo (o runtime usa Appwrite); `DATABASE_URL_PROD` nunca deve aparecer no exemplo de produção.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_env_example.py`:

```python
"""Paridade entre o que o backend le e o que o .env.example oferece."""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
EXEMPLO = (RAIZ / "infra/.env.example").read_text(encoding="utf-8")

CHAVES_EXIGIDAS = [
    "ENVIRONMENT",
    "SECRET_KEY",
    "WEBHOOK_SECRET",
    "CORS_ORIGINS",
    "REDIS_URL",
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_EMBED_MODEL",
    "APPWRITE_ENDPOINT",
    "APPWRITE_PROJECT_ID",
    "APPWRITE_API_KEY",
    "QDRANT_URL",
    "EVOLUTION_API_URL",
    "EVOLUTION_API_KEY",
    "N8N_ENCRYPTION_KEY",
    "EVOLUTION_INSTANCE",
    "BACKEND_URL",
]

SENSIVEIS = [
    "SECRET_KEY",
    "WEBHOOK_SECRET",
    "APPWRITE_API_KEY",
    "OPENAI_API_KEY",
    "EVOLUTION_API_KEY",
    "N8N_ENCRYPTION_KEY",
]


def _sem_aspas_externas(valor: str) -> str:
    """Remove UMA camada de aspas externas — é o que o `source` do bash faz.

    `CORS_ORIGINS='["http://localhost:3000"]'` chega ao processo como
    `["http://localhost:3000"]`; o valor "lógico" da chave é o JSON interno.
    """
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1]
    return valor


def _valores() -> dict[str, str]:
    valores: dict[str, str] = {}
    for linha in EXEMPLO.splitlines():
        if not linha or linha.lstrip().startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = _sem_aspas_externas(valor.strip())
    return valores


def test_exemplo_tem_todas_as_chaves_exigidas():
    valores = _valores()
    faltando = [chave for chave in CHAVES_EXIGIDAS if chave not in valores]

    assert faltando == []


def test_chaves_sensiveis_ficam_vazias_ou_com_placeholder():
    valores = _valores()
    for chave in SENSIVEIS:
        valor = valores[chave]
        assert valor == "" or re.search(r"(change|dev|exemplo|troque)", valor, re.I), (
            f"{chave} não pode ter valor real no exemplo: {valor!r}"
        )


def test_modelo_do_ollama_bate_com_o_default_do_backend():
    from app.core.config import Settings

    assert _valores()["OLLAMA_MODEL"] == Settings(_env_file=None).ollama_model


def test_cors_no_exemplo_e_lista_json():
    valor = _valores()["CORS_ORIGINS"]

    assert valor.startswith("[") and valor.endswith("]"), (
        "CORS_ORIGINS precisa ser lista JSON para o pydantic-settings"
    )
    assert json.loads(valor)


def test_cors_usa_aspas_simples_externas():
    """Armadilha do `source` (usado por `start-prod.sh`).

    Sem as aspas simples externas, o bash remove as aspas internas do JSON:
    `CORS_ORIGINS=["http://localhost:3000"]` chega ao processo como
    `[http://localhost:3000]` — JSON inválido para o pydantic-settings.
    Com `CORS_ORIGINS='["..."]'` o JSON sobrevive intacto.
    """
    linha = next(
        linha for linha in EXEMPLO.splitlines() if linha.startswith("CORS_ORIGINS=")
    )

    assert linha == "CORS_ORIGINS='[\"http://localhost:3000\"]'"


def test_exemplo_documenta_bloco_de_producao():
    assert "infra/.env.prod" in EXEMPLO
    linhas = [
        linha for linha in EXEMPLO.splitlines() if "https://app.emsoft.app" in linha
    ]
    assert linhas, "bloco de produção precisa citar o domínio público"
    assert any(
        linha.lstrip("# ").startswith("CORS_ORIGINS=") for linha in linhas
    ), "o domínio público precisa aparecer em CORS_ORIGINS"


def test_exemplo_nao_traz_database_url_prod():
    assert "DATABASE_URL_PROD" not in _valores()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_env_example.py -v`

Expected: FAIL — `OLLAMA_MODEL` é `deepseek-v4-flash:cloud`; `QDRANT_URL` ausente do exemplo; `CORS_ORIGINS` não é lista JSON.

- [ ] **Step 3: Write minimal implementation**

Em `infra/.env.example`, ajustar:

```dotenv
# === CORS ===
# Lista JSON. Em desenvolvimento basta o frontend local; em produção use só os
# domínios públicos (localhost é recusado por validate_production_secrets).
#
# ATENÇÃO: as aspas SIMPLES externas são obrigatórias. O `start-prod.sh` faz
# `source` deste arquivo e o bash remove aspas duplas não protegidas: sem as
# simples, `CORS_ORIGINS=["http://localhost:3000"]` chega ao pydantic como
# `[http://localhost:3000]` (JSON inválido). As aspas simples são consumidas
# pelo `source` e deixam o JSON intacto.
CORS_ORIGINS='["http://localhost:3000"]'
```

```dotenv
# === Qdrant ===
QDRANT_URL=http://localhost:6333
```

```dotenv
# Modelo de chat (requer: ollama pull llama3.2).
# A pilha de produção (infra/docker-compose.prod.yml) sobe Ollama local e baixa este
# modelo. Para usar Ollama Cloud, sobrescreva OLLAMA_MODEL no infra/.env.prod.
OLLAMA_MODEL=llama3.2
```

e acrescentar ao final:

```dotenv
# === Produção (infra/.env.prod) ===
# Copie este arquivo para infra/.env.prod e preencha. O compose de produção espera
# estas chaves; start-prod.sh falha se /health/ready não responder 200.
# ENVIRONMENT=production
# CORS_ORIGINS='["https://app.emsoft.app"]'
# OLLAMA_BASE_URL=http://ollama:11434
# QDRANT_URL=http://qdrant:6333
# APPWRITE_ENDPOINT=http://appwrite/v1
# DATABASE_URL_PROD não é usada: a store primária é Appwrite.
```

Em `backend/app/core/config.py`, o default já é `llama3.2` — **não** mude; o teste garante que exemplo e código não divirjam de novo.

> **Por que aspas simples (evidência, não preferência):** `source arquivo.env` com `CORS_ORIGINS=["http://localhost:3000"]` deixa a variável como `[http://localhost:3000]` — o bash come as aspas duplas internas e o `json.loads` do pydantic-settings falha no boot. Com `CORS_ORIGINS='["http://localhost:3000"]'` o `source` remove só a camada externa e o JSON chega intacto. O mesmo arquivo lido pelo `python-dotenv` (caso do `Settings` em dev) também devolve `["http://localhost:3000"]`. Ambos os caminhos foram verificados.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_env_example.py -v`

Expected: PASS (7 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add infra/.env.example backend/tests/test_env_example.py
git commit -m "docs(infra): env example com paridade de chaves e modelo unico

- QDRANT_URL e bloco de producao documentados
- CORS_ORIGINS passa a ser lista JSON entre aspas simples (o `source` do
  start-prod.sh remove aspas duplas internas e invalidaria o JSON)
- OLLAMA_MODEL alinhado ao modelo que a pilha prod baixa (llama3.2)
- teste de paridade impede novo drift entre Settings e exemplo"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 05 e 09)**

```
| 05-14 | Drift de modelo: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` | `core/config.py:31`; `infra/.env.example:26` | Média | **CORRIGIDO** — exemplo alinhado a `llama3.2` (modelo que a pilha prod baixa) e teste de paridade em `tests/test_env_example.py` |
| 09-10 | Drift de modelo Ollama entre `config.py` e `infra/.env.example` | `core/config.py:31`; `infra/.env.example:26` | Média | **CORRIGIDO** — mesma evidência da Task R0.5 (paridade verificada por teste) |
```

## Gate R0 — critério de saída

- [ ] `cd backend && uv run pytest tests/ -q && uv run ruff check app tests` verde.
- [ ] `docker network ls | grep -w appwrite` mostra a rede criada pela pilha do Appwrite; `docker compose -f infra/docker-compose.prod.yml config` é válido.
- [ ] `bash -n scripts/start-prod.sh` sem erro e o script **não** contém `alembic upgrade` nem `sleep 5`.
- [ ] Na raiz do repositório: `env -i bash -c 'set -a; source infra/.env.example; python3 -c "import json,os; json.loads(os.environ[\"CORS_ORIGINS\"])"'` não levanta erro — o JSON de `CORS_ORIGINS` sobrevive ao `source` (armadilha das aspas simples).
- [ ] Com a pilha de pé, `curl -f http://localhost:8000/health/ready` (ou `docker compose exec backend ...`) responde 200 com `status == "ok"`.
- [ ] Nenhum segredo literal em `infra/docker-compose.prod.yml` (todo valor sensível é `${VAR}`).

---

## R1 — Observabilidade e métricas

> **Gate de entrada: G3** (Fases 1–3 concluídas). As tasks abaixo consomem `chats.departamento_id` (F1.2/F1.8) e o escopo de `obter_dashboard(user=...)` (F1.9). Executar a R1 antes da F4 é obrigatório: o dashboard da Fase 4 exibe estes números.

### Task R1.1: Logging estruturado com correlation id

**Files:**
- Create: `backend/app/core/logging.py` (`JsonFormatter`, `configurar_logging`)
- Create: `backend/app/core/correlacao.py` (`CorrelacaoMiddleware`)
- Modify: `backend/app/main.py:8-60` (registrar middleware e configurar logging)
- Test: `backend/tests/test_logging_correlacao.py`

**Interfaces:**
- Produces:
  - `JsonFormatter` — uma linha JSON por registro com `ts`, `level`, `logger`, `msg`, `request_id`, `chat_id`, `event` (os três últimos quando disponíveis)
  - `configurar_logging(nivel: str = "INFO") -> None` — idempotente; em produção usa `JsonFormatter`, em desenvolvimento mantém o formato legível
  - `CorrelacaoMiddleware` — gera/reaproveita `X-Request-Id` (aceita 1–64 chars de `[A-Za-z0-9._-]`, senão gera novo), devolve o id no header da resposta e registra uma linha `event="requisicao"` com `metodo`, `rota`, `status` e `duracao_ms`
  - `chat_id_var: ContextVar[str | None]` — usado pelos services para amarrar eventos ao chat (Gap 12-6)

**Regra:** o id **nunca** vem do cliente sem validação (evita injeção de log) e nunca é um dado sensível. O middleware não loga corpo nem query string — só caminho, método, status e duração (C9).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_logging_correlacao.py`:

```python
"""Log JSON e correlacao de requisicao."""

import json
import logging

import pytest

from app.core.correlacao import CorrelacaoMiddleware
from app.core.logging import JsonFormatter, configurar_logging
from app.main import app


def _registro(msg: str = "oi", **extra) -> logging.LogRecord:
    registro = logging.LogRecord("app.teste", logging.INFO, __file__, 1, msg, None, None)
    for chave, valor in extra.items():
        setattr(registro, chave, valor)
    return registro


def test_formatter_serializa_campos_obrigatorios():
    saida = json.loads(JsonFormatter().format(_registro("mensagem", request_id="abc")))

    assert saida["level"] == "INFO"
    assert saida["logger"] == "app.teste"
    assert saida["msg"] == "mensagem"
    assert saida["request_id"] == "abc"
    assert saida["chat_id"] is None
    assert saida["ts"].endswith("+00:00")


def test_formatter_nao_quebra_com_excecao():
    try:
        raise ValueError("boom")
    except ValueError:
        registro = logging.LogRecord(
            "app.teste", logging.ERROR, __file__, 1, "falhou", None, __import__("sys").exc_info()
        )

    saida = json.loads(JsonFormatter().format(registro))

    assert "ValueError: boom" in saida["exc"]


def test_configurar_logging_e_idempotente():
    configurar_logging("DEBUG")
    configurar_logging("DEBUG")

    handlers = [h for h in logging.getLogger().handlers if getattr(h, "_emsoft_json", False)]

    assert len(handlers) == 1


@pytest.mark.asyncio
async def test_middleware_reaproveita_request_id_valido(client, caplog):
    caplog.set_level(logging.INFO)

    resp = await client.get("/health", headers={"X-Request-Id": "abc-123"})

    assert resp.headers["X-Request-Id"] == "abc-123"
    registro = next(r for r in caplog.records if getattr(r, "event", None) == "requisicao")
    assert registro.request_id == "abc-123"
    assert registro.rota == "/health"
    assert registro.status == 200


@pytest.mark.asyncio
async def test_middleware_descarta_request_id_invalido(client):
    resp = await client.get("/health", headers={"X-Request-Id": "x" * 200})

    assert resp.headers["X-Request-Id"] != "x" * 200
    assert 0 < len(resp.headers["X-Request-Id"]) <= 64


@pytest.mark.asyncio
async def test_middleware_gera_id_quando_ausente(client):
    resp = await client.get("/health")

    assert len(resp.headers["X-Request-Id"]) == 32


def test_middleware_esta_registrado():
    nomes = [m.cls.__name__ for m in app.user_middleware]

    assert "CorrelacaoMiddleware" in nomes
    assert CorrelacaoMiddleware is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_logging_correlacao.py -v`

Expected: FAIL — `ModuleNotFoundError: app.core.logging` e `app.core.correlacao`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/core/correlacao.py`:

```python
"""Correlation id por requisicao, com log de acesso estruturado."""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.acesso")

chat_id_var: ContextVar[str | None] = ContextVar("chat_id", default=None)

_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def novo_request_id() -> str:
    return uuid.uuid4().hex


class CorrelacaoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        recebido = request.headers.get("X-Request-Id", "")
        request_id = recebido if _ID_VALIDO.match(recebido) else novo_request_id()
        request.state.request_id = request_id
        inicio = time.perf_counter()

        resposta = await call_next(request)

        resposta.headers["X-Request-Id"] = request_id
        logger.info(
            "requisicao",
            extra={
                "request_id": request_id,
                "event": "requisicao",
                "metodo": request.method,
                "rota": request.url.path,
                "status": resposta.status_code,
                "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
                "chat_id": chat_id_var.get(),
            },
        )
        return resposta
```

`backend/app/core/logging.py`:

```python
"""Log estruturado: uma linha JSON por evento em producao."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.core.correlacao import chat_id_var

_CAMPOS = ("request_id", "chat_id", "event", "metodo", "rota", "status", "duracao_ms")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for campo in _CAMPOS:
            valor = getattr(record, campo, None)
            if campo == "chat_id" and valor is None:
                valor = chat_id_var.get()
            dados[campo] = valor
        if record.exc_info:
            dados["exc"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    if any(getattr(h, "_emsoft_json", False) for h in raiz.handlers):
        return

    handler = logging.StreamHandler()
    handler._emsoft_json = True  # type: ignore[attr-defined]
    if settings.environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        # Em dev o formato e legivel e NAO referencia campos opcionais: um
        # "%(request_id)s" fixo quebraria todo log emitido fora de requisicao.
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    raiz.addHandler(handler)
```

> O `JsonFormatter` usa `getattr(record, campo, None)` para todos os campos extras — por isso nenhum registro quebra por falta de `request_id`/`chat_id`, nem em produção nem em dev. O teste não depende do formato de dev.

Em `backend/app/main.py`:

```python
from app.core.correlacao import CorrelacaoMiddleware
from app.core.logging import configurar_logging

configurar_logging()

app = FastAPI(...)
app.add_middleware(CorrelacaoMiddleware)
```

(o `add_middleware` do CORS continua existindo; a ordem final é CORS por fora, correlação por dentro — o log de acesso enxerga o request já com CORS aplicado)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_logging_correlacao.py -v`

Expected: PASS (7 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/logging.py backend/app/core/correlacao.py backend/app/main.py \
  backend/tests/test_logging_correlacao.py
git commit -m "feat(observabilidade): log json com correlation id

- JsonFormatter expoe ts/level/logger/msg/request_id/chat_id/event
- middleware reaproveita X-Request-Id valido e gera hex de 32 quando ausente
- linha de acesso com metodo, rota, status e duracao_ms
- contextvar de chat_id preparada para eventos de dominio"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 08 e 12)**

```
| 08-5 | Sem logging estruturado nem request-id/correlação | `app/**` | Média | **CORRIGIDO** — `core/logging.py` (`JsonFormatter`) + `core/correlacao.py` (`CorrelacaoMiddleware`, `X-Request-Id`) |
| 12-6 | Logs sem correlation/event key | `app/**` | Média | **CORRIGIDO** — todo log de acesso carrega `request_id` e `event`; `chat_id` via `ContextVar` |
```

---

### Task R1.2: `tempo_medio_resposta` com semântica correta

**Files:**
- Modify: `backend/app/services/dashboard_service.py:44-59`
- Test: `backend/tests/test_dashboard_tempo_resposta.py`

**Interfaces:**
- Produces:
  - `DashboardService.tempo_medio_primeira_resposta(mensagens: list[dict]) -> float | None` — média, em segundos, do intervalo entre a **primeira** mensagem do cliente e a **primeira** mensagem de atendente **posterior** a ela, por chat; `None` quando nenhum chat se qualifica
  - `obter_dashboard` passa a usar essa função e mantém a chave `kpis.tempo_medio_resposta` (shape inalterado)

**Regra:** chats sem mensagem de cliente ou sem resposta humana não entram na média (não valem zero nem `None`); mensagem de atendente anterior à do cliente é ignorada. Datas são parseadas com `_parse_dt` (já existe) e mensagens sem `created_at` são descartadas.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_dashboard_tempo_resposta.py`:

```python
"""tempo_medio_resposta mede a primeira resposta humana por chat."""

import pytest

from app.services.dashboard_service import DashboardService


def _msg(chat: str, remetente: str, quando: str) -> dict:
    return {"chat_id": chat, "remetente": remetente, "created_at": quando}


def test_media_do_intervalo_ate_a_primeira_resposta():
    mensagens = [
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:02:00+00:00"),
        _msg("c1", "cliente", "2026-11-01T10:10:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:20:00+00:00"),
        _msg("c2", "cliente", "2026-11-01T11:00:00+00:00"),
        _msg("c2", "ia", "2026-11-01T11:00:05+00:00"),
        _msg("c2", "atendente", "2026-11-01T11:05:00+00:00"),
    ]

    resultado = DashboardService.tempo_medio_primeira_resposta(mensagens)

    assert resultado == 210.0  # (120 + 300) / 2


def test_ignora_chat_sem_resposta_humana():
    mensagens = [
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "ia", "2026-11-01T10:00:03+00:00"),
        _msg("c2", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c2", "atendente", "2026-11-01T10:01:00+00:00"),
    ]

    assert DashboardService.tempo_medio_primeira_resposta(mensagens) == 60.0


def test_ignora_resposta_anterior_ao_cliente():
    mensagens = [
        _msg("c1", "atendente", "2026-11-01T09:59:00+00:00"),
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:03:00+00:00"),
    ]

    assert DashboardService.tempo_medio_primeira_resposta(mensagens) == 180.0


def test_sem_dados_suficientes_devolve_none():
    assert DashboardService.tempo_medio_primeira_resposta([]) is None
    assert (
        DashboardService.tempo_medio_primeira_resposta(
            [_msg("c1", "cliente", "2026-11-01T10:00:00+00:00")]
        )
        is None
    )


@pytest.mark.asyncio
async def test_dashboard_usa_a_nova_metrica(fake_repos):
    cliente = await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    chat = await fake_repos.chats.create({"cliente_id": cliente["id"], "status": "NOVO"})
    # FakeStore.create sobrescreve created_at; o horario e fixado pelo update.
    msg_cliente = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    await fake_repos.mensagens.update(
        msg_cliente["id"], {"created_at": "2026-11-01T10:00:00+00:00"}
    )
    msg_atendente = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "atendente", "conteudo": "ola"}
    )
    await fake_repos.mensagens.update(
        msg_atendente["id"], {"created_at": "2026-11-01T10:01:00+00:00"}
    )

    dados = await DashboardService(fake_repos).obter_dashboard(user=None)

    assert dados["kpis"]["tempo_medio_resposta"] == 60.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_dashboard_tempo_resposta.py -v`

Expected: FAIL — `AttributeError: tempo_medio_primeira_resposta` e o KPI calculado por diferença entre mensagens do mesmo atendente.

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/dashboard_service.py`, acrescentar como método estático de `DashboardService`:

```python
    @staticmethod
    def tempo_medio_primeira_resposta(mensagens: list[dict]) -> float | None:
        """Segundos entre a primeira mensagem do cliente e a primeira resposta humana."""
        por_chat: dict[str, list[dict]] = {}
        for mensagem in mensagens:
            if not mensagem.get("created_at") or not mensagem.get("chat_id"):
                continue
            por_chat.setdefault(mensagem["chat_id"], []).append(mensagem)

        tempos: list[float] = []
        for lista in por_chat.values():
            do_cliente = [
                _parse_dt(m["created_at"])
                for m in lista
                if m.get("remetente") == RemetenteMensagem.cliente.value
            ]
            humanas = [
                _parse_dt(m["created_at"])
                for m in lista
                if m.get("remetente") == RemetenteMensagem.atendente.value
            ]
            if not do_cliente or not humanas:
                continue
            primeira_cliente = min(do_cliente)
            resposta = min((d for d in humanas if d > primeira_cliente), default=None)
            if resposta is None:
                continue
            tempos.append((resposta - primeira_cliente).total_seconds())

        if not tempos:
            return None
        return round(sum(tempos) / len(tempos), 0)
```

e substituir o bloco `# tempo médio de resposta (atendente)` por:

```python
        mensagens = await self.repos.mensagens.list_all()
        tempo_medio = self.tempo_medio_primeira_resposta(mensagens)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_dashboard_tempo_resposta.py -v`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/dashboard_service.py backend/tests/test_dashboard_tempo_resposta.py
git commit -m "fix(dashboard): tempo medio mede a primeira resposta humana

- media por chat entre a primeira mensagem do cliente e a primeira resposta
- chats sem resposta humana nao entram na media
- resposta anterior ao cliente e ignorada
- shape do dashboard preservado (kpis.tempo_medio_resposta)"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 00 e 08)**

```
| 00-10 | `tempo_medio_resposta` mede intervalo entre mensagens do mesmo atendente, não o tempo de primeira resposta | `services/dashboard_service.py:44-59` | **Alta** | **CORRIGIDO** — `DashboardService.tempo_medio_primeira_resposta` (cliente → primeira resposta humana, por chat) com teste em `tests/test_dashboard_tempo_resposta.py` |
```

---

### Task R1.3: Métricas de produto (resolução confirmada, transbordo, duplicidade)

**Files:**
- Create: `backend/app/services/metricas_service.py`
- Modify: `backend/app/services/dashboard_service.py` (extrai `escopo_visivel(user)` do fecho inline da F1.9)
- Modify: `backend/app/api/routes/dashboard.py` (nova rota) e `backend/app/schemas/dashboard.py`
- Test: `backend/tests/test_metricas_service.py`

**Interfaces:**
- Produces:
  - `escopo_visivel(user: dict | None) -> Callable[[dict], bool]` em `dashboard_service.py` — regra única de visibilidade (mesma da F1.9), usada por `obter_dashboard` e por `MetricasService`
  - `MetricasService(repos).calcular(user=None, departamento_id=None, inicio=None, fim=None) -> dict`:
    ```
    {
      "periodo": {"inicio": str|None, "fim": str|None},
      "total": int,
      "resolucao_confirmada": int,
      "taxa_resolucao_confirmada": float,
      "transbordo": int,
      "taxa_transbordo": float,
      "clientes_com_duplicidade": int,
      "chats_duplicados": int,
      "por_departamento": [
        {"departamento_id": str|None, "total": int, "resolvidos": int,
         "transbordo": int, "tempo_medio_primeira_resposta": float|None}
      ],
    }
    ```
  - `GET /dashboard/metricas?departamento_id=&inicio=&fim=` → esse dicionário

**Definições (spec 00 / 08-9) — fixadas aqui para não haver interpretação livre:**

| Métrica | Definição |
|---|---|
| `resolucao_confirmada` | chats com `status == "RESOLVIDO"` no período (confirmação explícita; `ENCERRADO` não conta) |
| `transbordo` | chats com `necessita_humano is True` |
| `clientes_com_duplicidade` | clientes com **mais de um** chat no recorte |
| `chats_duplicados` | soma de `(chats do cliente - 1)` nos clientes com duplicidade |
| `tempo_medio_primeira_resposta` | reaproveita `DashboardService.tempo_medio_primeira_resposta` (R1.2) sobre as mensagens dos chats do departamento |

**Regra:** `inicio`/`fim` são datas ISO (`YYYY-MM-DD` ou ISO-8601 completo) comparadas com `chats.created_at`; `fim` é inclusivo até o fim do dia quando vem só a data. Escopo RBAC vem de `escopo_visivel(user)` e é aplicado **antes** do filtro de departamento (mesma ordem da F1.9 — nunca amplia visão).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_metricas_service.py`:

```python
"""Metricas de produto com semantica fixada (spec 00 / gap 08-9)."""

import pytest

from app.services.metricas_service import MetricasService


async def _cenario(fake_repos):
    d1 = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    d2 = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    cli1 = await fake_repos.clientes.create({"nome": "A", "documento": "1"})
    cli2 = await fake_repos.clientes.create({"nome": "B", "documento": "2"})

    resolvido = await fake_repos.chats.create(
        {
            "cliente_id": cli1["id"],
            "status": "RESOLVIDO",
            "departamento_id": d1["id"],
            "necessita_humano": False,
        }
    )
    transbordo = await fake_repos.chats.create(
        {
            "cliente_id": cli1["id"],
            "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
            "departamento_id": d1["id"],
            "necessita_humano": True,
        }
    )
    novo = await fake_repos.chats.create(
        {
            "cliente_id": cli2["id"],
            "status": "NOVO",
            "departamento_id": d2["id"],
            "necessita_humano": False,
        }
    )
    return d1, d2, resolvido, transbordo, novo


@pytest.mark.asyncio
async def test_conta_resolucao_transbordo_e_duplicidade(fake_repos):
    d1, d2, _, _, _ = await _cenario(fake_repos)

    dados = await MetricasService(fake_repos).calcular()

    assert dados["total"] == 3
    assert dados["resolucao_confirmada"] == 1
    assert dados["taxa_resolucao_confirmada"] == pytest.approx(0.3333, abs=1e-4)
    assert dados["transbordo"] == 1
    assert dados["clientes_com_duplicidade"] == 1
    assert dados["chats_duplicados"] == 1
    assert {linha["departamento_id"] for linha in dados["por_departamento"]} == {
        d1["id"],
        d2["id"],
    }


@pytest.mark.asyncio
async def test_recorte_por_departamento(fake_repos):
    d1, d2, _, _, _ = await _cenario(fake_repos)

    dados = await MetricasService(fake_repos).calcular(departamento_id=d1["id"])

    assert dados["total"] == 2
    assert dados["resolucao_confirmada"] == 1
    assert [linha["departamento_id"] for linha in dados["por_departamento"]] == [d1["id"]]

    outro = await MetricasService(fake_repos).calcular(departamento_id=d2["id"])
    assert outro["total"] == 1


@pytest.mark.asyncio
async def test_atendente_sem_departamento_nao_ve_fila_global(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": None}

    dados = await MetricasService(fake_repos).calcular(user=user)

    assert dados["total"] == 0


@pytest.mark.asyncio
async def test_atendente_ve_apenas_o_proprio_departamento(fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": d1["id"]}

    dados = await MetricasService(fake_repos).calcular(user=user)

    assert dados["total"] == 2
    assert [linha["departamento_id"] for linha in dados["por_departamento"]] == [d1["id"]]


@pytest.mark.asyncio
async def test_janela_por_data_recorta_os_chats(fake_repos):
    _, _, resolvido, _, _ = await _cenario(fake_repos)
    await fake_repos.chats.update(
        resolvido["id"], {"created_at": "2026-10-01T10:00:00+00:00"}
    )

    dados = await MetricasService(fake_repos).calcular(inicio="2026-11-01", fim="2026-11-30")

    assert dados["total"] == 2


@pytest.mark.asyncio
async def test_tempo_medio_por_departamento(fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    chat = (await fake_repos.chats.list_all())[0]
    cliente_msg = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    await fake_repos.mensagens.update(
        cliente_msg["id"], {"created_at": "2026-11-01T10:00:00+00:00"}
    )
    atendente_msg = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "atendente", "conteudo": "ola"}
    )
    await fake_repos.mensagens.update(
        atendente_msg["id"], {"created_at": "2026-11-01T10:01:00+00:00"}
    )

    dados = await MetricasService(fake_repos).calcular(departamento_id=d1["id"])

    linha_d1 = next(
        linha for linha in dados["por_departamento"] if linha["departamento_id"] == d1["id"]
    )
    assert linha_d1["tempo_medio_primeira_resposta"] == 60.0


@pytest.mark.asyncio
async def test_rota_de_metricas_exige_sessao_e_escopa(client, atendente_token, fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(atendente["id"], {"departamento_id": d1["id"]})

    sem_sessao = await client.get("/dashboard/metricas")
    com_sessao = await client.get(
        "/dashboard/metricas",
        params={"departamento_id": d1["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert sem_sessao.status_code == 401
    assert com_sessao.status_code == 200
    assert com_sessao.json()["total"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_metricas_service.py -v`

Expected: FAIL — `ModuleNotFoundError: app.services.metricas_service` e 404 em `/dashboard/metricas`.

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/dashboard_service.py`, extrair da F1.9 (o fecho `no_escopo` dentro de `obter_dashboard`) para o topo do módulo:

```python
def escopo_visivel(user: dict | None):
    """Predicado de visibilidade de chats, igual ao aplicado no dashboard."""
    if not user or user.get("perfil") != "atendente":
        return lambda chat: True

    departamento_id = user.get("departamento_id")
    usuario_id = user["id"]

    def pode_ver(chat: dict) -> bool:
        if chat.get("atendente_id") == usuario_id:
            return True
        if chat.get("atendente_id") is not None:
            return False
        if departamento_id:
            return chat.get("departamento_id") == departamento_id
        return (
            chat.get("departamento_id") is None
            and chat.get("setor_alvo") is not None
            and chat.get("setor_alvo") == user.get("setor")
        )

    return pode_ver
```

e dentro de `obter_dashboard` usar `pode_ver = escopo_visivel(user)` no lugar do fecho inline (comportamento idêntico — os testes da F1.9 continuam valendo).

`backend/app/services/metricas_service.py`:

```python
"""Metricas de produto derivadas dos chats (spec 00 / gap 08-9)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.services.dashboard_service import DashboardService, _parse_dt, escopo_visivel


def _limite(valor: str | None, fim_do_dia: bool) -> datetime | None:
    if not valor:
        return None
    if len(valor) == 10:
        dia = date.fromisoformat(valor)
        base = datetime.combine(dia, time.max if fim_do_dia else time.min)
        return base.replace(tzinfo=UTC)
    return _parse_dt(valor)


class MetricasService:
    def __init__(self, repos: Repositories) -> None:
        self.repos = repos

    async def calcular(
        self,
        user: dict | None = None,
        departamento_id: str | None = None,
        inicio: str | None = None,
        fim: str | None = None,
    ) -> dict:
        pode_ver = escopo_visivel(user)
        desde = _limite(inicio, fim_do_dia=False)
        ate = _limite(fim, fim_do_dia=True)

        chats = [c for c in await self.repos.chats.list_all() if pode_ver(c)]
        if departamento_id:
            chats = [c for c in chats if c.get("departamento_id") == departamento_id]
        if desde or ate:
            recortados = []
            for chat in chats:
                criado = chat.get("created_at")
                if not criado:
                    continue
                quando = _parse_dt(criado)
                if desde and quando < desde:
                    continue
                if ate and quando > ate:
                    continue
                recortados.append(chat)
            chats = recortados

        total = len(chats)
        resolvidos = sum(1 for c in chats if c.get("status") == StatusChat.resolvido.value)
        transbordo = sum(1 for c in chats if c.get("necessita_humano") is True)

        por_cliente: dict[str, int] = {}
        for chat in chats:
            cliente_id = chat.get("cliente_id")
            if cliente_id:
                por_cliente[cliente_id] = por_cliente.get(cliente_id, 0) + 1
        duplicados = [qtd for qtd in por_cliente.values() if qtd > 1]

        mensagens = await self.repos.mensagens.list_all()
        ids_visiveis = {c["id"] for c in chats}

        departamentos: dict[str | None, list[dict]] = {}
        for chat in chats:
            departamentos.setdefault(chat.get("departamento_id"), []).append(chat)

        por_departamento = []
        for depto, lista in sorted(departamentos.items(), key=lambda item: item[0] or ""):
            ids = {c["id"] for c in lista}
            por_departamento.append(
                {
                    "departamento_id": depto,
                    "total": len(lista),
                    "resolvidos": sum(
                        1 for c in lista if c.get("status") == StatusChat.resolvido.value
                    ),
                    "transbordo": sum(1 for c in lista if c.get("necessita_humano") is True),
                    "tempo_medio_primeira_resposta": (
                        DashboardService.tempo_medio_primeira_resposta(
                            [m for m in mensagens if m.get("chat_id") in ids]
                        )
                    ),
                }
            )

        do_escopo = [m for m in mensagens if m.get("chat_id") in ids_visiveis]

        return {
            "periodo": {"inicio": inicio, "fim": fim},
            "total": total,
            "resolucao_confirmada": resolvidos,
            "taxa_resolucao_confirmada": round(resolvidos / total, 4) if total else 0.0,
            "transbordo": transbordo,
            "taxa_transbordo": round(transbordo / total, 4) if total else 0.0,
            "clientes_com_duplicidade": len(duplicados),
            "chats_duplicados": sum(qtd - 1 for qtd in duplicados),
            "por_departamento": por_departamento,
            "tempo_medio_primeira_resposta": (
                DashboardService.tempo_medio_primeira_resposta(do_escopo)
            ),
        }
```

Em `backend/app/schemas/dashboard.py`, acrescentar:

```python
class MetricaDepartamento(BaseModel):
    departamento_id: str | None = None
    total: int
    resolvidos: int
    transbordo: int
    tempo_medio_primeira_resposta: float | None = None


class MetricasResponse(BaseModel):
    periodo: dict[str, str | None]
    total: int
    resolucao_confirmada: int
    taxa_resolucao_confirmada: float
    transbordo: int
    taxa_transbordo: float
    clientes_com_duplicidade: int
    chats_duplicados: int
    por_departamento: list[MetricaDepartamento]
    tempo_medio_primeira_resposta: float | None = None
```

Em `backend/app/api/routes/dashboard.py`:

```python
@router.get("/metricas", response_model=MetricasResponse)
async def obter_metricas(
    departamento_id: str | None = Query(None),
    inicio: str | None = Query(None),
    fim: str | None = Query(None),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = MetricasService(repos)
    return await service.calcular(
        user=user, departamento_id=departamento_id, inicio=inicio, fim=fim
    )
```

> A rota `/metricas` é declarada **antes** de qualquer rota com `/{chat_id}` no mesmo router — hoje o router do dashboard só tem `GET ""`, então não há colisão; se uma rota parametrizada entrar depois, ela precisa vir por último.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_metricas_service.py -v`

Expected: PASS (7 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

Expected: suíte inteira verde — inclusive `tests/test_visibilidade_departamento.py` da F1.9, que passa a exercitar `escopo_visivel`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/metricas_service.py backend/app/services/dashboard_service.py \
  backend/app/api/routes/dashboard.py backend/app/schemas/dashboard.py \
  backend/tests/test_metricas_service.py
git commit -m "feat(dashboard): metricas de produto com recorte por departamento

- resolucao confirmada, transbordo e duplicidade com definicao explicita
- recorte por departamento e janela de datas
- escopo RBAC extraido para escopo_visivel (fonte unica com a F1.9)
- tempo medio por departamento reaproveita a metrica da R1.2"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 08 e 00)**

```
| 08-9 | Métricas de produto (resolução confirmada, transbordo, roteamento, duplicidade) sem instrumentação; `tempo_medio_resposta` com semântica errada | `services/dashboard_service.py` | **Alta** | **CORRIGIDO** — `MetricasService.calcular` + `GET /dashboard/metricas` (Tasks R1.2/R1.3) |
| 00-16 | Indicadores de sucesso por departamento/duplicidade sem instrumentação | `services/dashboard_service.py` | Média | **CORRIGIDO** — `por_departamento` e `clientes_com_duplicidade` em `MetricasService` (Task R1.3) |
```

---

### Task R1.4: Health degradado do bootstrap

**Files:**
- Modify: `backend/app/appwrite/bootstrap.py:100-106` (`ensure_appwrite_schema` devolve relatório)
- Modify: `backend/app/services/health_service.py` (`build_health_service` recebe `schema_status`)
- Modify: `backend/app/main.py:28-40` (lifespan sem `try/except` cego)
- Test: `backend/tests/test_bootstrap_health.py`

**Interfaces:**
- Produces:
  - `ensure_appwrite_schema(databases) -> dict` → `{"ok": bool, "erro": str | None}`; **não levanta**
  - `build_health_service(databases, schema_status: dict) -> HealthService` com as sondas `appwrite` (chamada real a `list()`) e `schema` (falha quando `schema_status["ok"]` é falso)
  - `app.state.schema_status` populado no `lifespan`

**Regra:** a API continua subindo com Appwrite fora (comportamento atual), mas deixa de esconder o problema: `/health/ready` responde **503** e a linha de log traz o erro. Isso é o que permite ao orquestrador não mandar tráfego para uma instância sem schema.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_bootstrap_health.py`:

```python
"""Bootstrap degradado e visivel no readiness."""

from types import SimpleNamespace

import pytest

from app.appwrite.bootstrap import ensure_appwrite_schema
from app.appwrite.schema import COLLECTIONS, DB_ID
from app.main import app
from app.services.health_service import build_health_service


class DatabasesExistente:
    """Appwrite ja provisionado: nada deve ser criado."""

    def __init__(self) -> None:
        self.criados: list[tuple] = []

    def list(self):
        return SimpleNamespace(databases=[SimpleNamespace(id=DB_ID)])

    def list_collections(self, database_id):
        return SimpleNamespace(
            collections=[SimpleNamespace(id=c) for c in COLLECTIONS]
        )

    def list_attributes(self, database_id, collection_id):
        return SimpleNamespace(
            attributes=[
                SimpleNamespace(key=a["key"])
                for a in COLLECTIONS[collection_id]["attributes"]
            ]
        )

    def create(self, *args, **kwargs):
        self.criados.append(("database", args))

    def create_collection(self, *args, **kwargs):
        self.criados.append(("collection", args))

    def create_string_attribute(self, *args, **kwargs):
        self.criados.append(("string", args))

    create_integer_attribute = create_string_attribute
    create_float_attribute = create_string_attribute
    create_boolean_attribute = create_string_attribute
    create_datetime_attribute = create_string_attribute
    create_enum_attribute = create_string_attribute


class DatabasesQuebrado:
    def list(self):
        raise RuntimeError("appwrite fora do ar")


def test_bootstrap_provisionado_nao_cria_nada():
    databases = DatabasesExistente()

    resultado = ensure_appwrite_schema(databases)

    assert resultado == {"ok": True, "erro": None}
    assert databases.criados == []


def test_bootstrap_falho_devolve_erro_sem_levantar():
    resultado = ensure_appwrite_schema(DatabasesQuebrado())

    assert resultado["ok"] is False
    assert "appwrite fora do ar" in resultado["erro"]


@pytest.mark.asyncio
async def test_schema_falho_degrada_readiness():
    saude = build_health_service(
        DatabasesQuebrado(), {"ok": False, "erro": "appwrite fora do ar"}
    )

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["schema"]["ok"] is False
    assert resultado["checks"]["appwrite"]["ok"] is False


@pytest.mark.asyncio
async def test_schema_ok_mantem_readiness_verde():
    saude = build_health_service(DatabasesExistente(), {"ok": True, "erro": None})

    resultado = await saude.pronto()

    assert resultado["status"] == "ok"


@pytest.mark.asyncio
async def test_rota_ready_reporta_schema_degradado(client):
    app.state.saude = build_health_service(
        DatabasesExistente(), {"ok": False, "erro": "bootstrap incompleto"}
    )

    resp = await client.get("/health/ready")

    assert resp.status_code == 503
    assert resp.json()["checks"]["schema"] == {
        "ok": False,
        "erro": "RuntimeError: bootstrap incompleto",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_bootstrap_health.py -v`

Expected: FAIL — `ensure_appwrite_schema` devolve `None`; `build_health_service` aceita só um argumento.

- [ ] **Step 3: Write minimal implementation**

`backend/app/appwrite/bootstrap.py` — substituir `ensure_appwrite_schema`:

```python
def ensure_appwrite_schema(databases: Databases) -> dict:
    """Cria database, collections e attributes se ainda não existirem.

    Nunca levanta: devolve um relatório para o readiness reportar degradação.
    """
    try:
        ensure_database(databases)
        for collection_id, spec in COLLECTIONS.items():
            ensure_collection(databases, collection_id, spec["name"])
            ensure_attributes(databases, collection_id, spec["attributes"])
    except Exception as exc:  # noqa: BLE001 - bootstrap nao derruba a API
        logger.exception("Appwrite: falha ao garantir o schema")
        return {"ok": False, "erro": f"{type(exc).__name__}: {exc}"[:200]}
    return {"ok": True, "erro": None}
```

`backend/app/services/health_service.py` — substituir `build_health_service`:

```python
def build_health_service(databases, schema_status: dict) -> HealthService:
    async def appwrite_ok() -> None:
        databases.list()

    async def schema_ok() -> None:
        if not schema_status.get("ok"):
            raise RuntimeError(schema_status.get("erro") or "schema indisponivel")

    return HealthService({"appwrite": appwrite_ok, "schema": schema_ok})
```

`backend/app/main.py` — no `lifespan`, trocar o `try/except` por:

```python
    app.state.schema_status = ensure_appwrite_schema(app.state.appwrite_databases)
    app.state.saude = build_health_service(
        app.state.appwrite_databases, app.state.schema_status
    )
    if not app.state.schema_status["ok"]:
        logger.error("Appwrite: schema degradado (%s)", app.state.schema_status["erro"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_bootstrap_health.py -v`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

Expected: verde, incluindo `tests/test_health_ready.py` da R0.2 — aqueles testes constroem `HealthService(...)` diretamente, então não sentem a mudança de assinatura de `build_health_service`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/appwrite/bootstrap.py backend/app/services/health_service.py \
  backend/app/main.py backend/tests/test_bootstrap_health.py
git commit -m "feat(health): bootstrap degradado fica visivel no readiness

- ensure_appwrite_schema devolve relatorio e nunca levanta
- /health/ready checa appwrite e schema (503 quando um falha)
- app.state.schema_status registra o resultado do boot"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 08 e 02)**

```
| 08-12 | Health check degradado do bootstrap não implementado | `appwrite/bootstrap.py` | Média | **CORRIGIDO** — `ensure_appwrite_schema` devolve relatório e a sonda `schema` de `/health/ready` responde 503 (Task R1.4) |
| 02-10 | Bootstrap aditivo não propaga mudança de enum; health degradado não implementado | `appwrite/bootstrap.py` | **Alta** | **ABERTO (parcial)** — health degradado fechado (Task R1.4); propagação de enum segue em R0.4/F1.1 (atualização manual documentada) |
```

## Gate R1 — critério de saída

- [ ] `cd backend && uv run pytest tests/ -q && uv run ruff check app tests` verde.
- [ ] `GET /health/ready` responde 200 com `checks` de `appwrite` e `schema`; derrubar o Appwrite devolve 503 sem derrubar a API.
- [ ] Toda linha de log de acesso é JSON (em `ENVIRONMENT=production`) com `request_id`, `event`, `metodo`, `rota`, `status`, `duracao_ms`.
- [ ] `GET /dashboard/metricas` devolve `resolucao_confirmada`, `transbordo`, `clientes_com_duplicidade` e `por_departamento` com números conferidos à mão em um conjunto pequeno de chats.
- [ ] `kpis.tempo_medio_resposta` mede cliente → primeira resposta humana (verificado no teste e em um chat real).

---

## R2 — Duração

> **Gate de entrada: G4** (Fases 1–4 + R0 + R1 concluídas). Nada aqui bloqueia a entrega; tudo aqui impede a regressão silenciosa depois dela.

### Task R2.1: Um único Python (3.12) e remoção do `openai` não usado

**Files:**
- Modify: `backend/pyproject.toml` (`requires-python`, `[tool.ruff] target-version`, `[tool.mypy] python_version`, remover `openai`)
- Modify: `backend/requirements.txt` (remover `openai`)
- Modify: `.github/workflows/ci.yml` (`python-version: "3.12"`)
- Test: `backend/tests/test_versoes_python.py`

**Interfaces:**
- Produces: `requires-python = ">=3.12"`, ruff `target-version = "py312"`, mypy `python_version = "3.12"`, CI em 3.12 — igual ao `backend/Dockerfile` (`python:3.12-slim`), que é o que roda em produção.

**Decisão:** o runtime manda. Alinhar CI/lint/mypy **ao** Dockerfile (3.12) e não o contrário — reduzir o runtime para 3.11 ganharia nada e arriscaria comportamento diferente do que é testado. `openai` sai porque `app/ai/openai_service.py` fala com a API via `httpx`, sem importar o pacote (Gap 05-19).

- [ ] **Step 0: Medir antes de mudar**

Run: `cd backend && uv run pytest tests/ -q --tb=no | tail -3`

Anote o total de testes — a mudança de versão não pode reduzir a contagem.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_versoes_python.py`:

```python
"""Uma unica versao de Python no projeto, igual ao Dockerfile."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((RAIZ / "backend/pyproject.toml").read_text(encoding="utf-8"))
DOCKERFILE = (RAIZ / "backend/Dockerfile").read_text(encoding="utf-8")
CI = (RAIZ / ".github/workflows/ci.yml").read_text(encoding="utf-8")
REQUIREMENTS = (RAIZ / "backend/requirements.txt").read_text(encoding="utf-8")


def test_dockerfile_usa_312():
    assert "python:3.12-slim" in DOCKERFILE


def test_pyproject_alinha_com_o_dockerfile():
    assert PYPROJECT["project"]["requires-python"] == ">=3.12"
    assert PYPROJECT["tool"]["ruff"]["target-version"] == "py312"
    assert PYPROJECT["tool"]["mypy"]["python_version"] == "3.12"


def test_ci_usa_312():
    assert 'python-version: "3.12"' in CI
    assert 'python-version: "3.11"' not in CI


def test_openai_nao_e_dependencia():
    deps = PYPROJECT["project"]["dependencies"]
    assert not [d for d in deps if d.startswith("openai")]
    assert "openai" not in REQUIREMENTS


def test_provider_segue_em_httpx():
    texto = (RAIZ / "backend/app/ai/openai_service.py").read_text(encoding="utf-8")

    assert "httpx" in texto
    assert "import openai" not in texto
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_versoes_python.py -v`

Expected: FAIL — `requires-python` é `>=3.11`, ruff `py311`, mypy `3.11`, CI `3.11`, `openai` presente.

- [ ] **Step 3: Write minimal implementation**

`backend/pyproject.toml`:

```toml
requires-python = ">=3.12"
```

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
```

```toml
[tool.mypy]
python_version = "3.12"
```

e remover a linha `"openai>=1.40.0",` das dependências.

`backend/requirements.txt`: remover `openai>=1.40.0`.

`.github/workflows/ci.yml`:

```yaml
      - name: Set up uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
```

Atualizar o lock e rodar a suíte:

```bash
cd backend && uv lock && uv sync --frozen --extra dev
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_versoes_python.py -v`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

Expected: mesma contagem (ou maior) do Step 0, verde.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/requirements.txt \
  .github/workflows/ci.yml backend/tests/test_versoes_python.py
git commit -m "build(backend): python 3.12 unico e remocao do openai nao usado

- requires-python, ruff, mypy e CI alinhados ao Dockerfile (3.12)
- openai removido do pyproject/requirements (provider usa httpx)
- teste de versao impede novo drift"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09 e 05)**

```
| 09-9 | Drift Python: pyproject/ruff/mypy/CI em 3.11 vs `Dockerfile` `3.12-slim` | `pyproject.toml`; `backend/Dockerfile`; `ci.yml` | Baixa | **CORRIGIDO** — tudo em 3.12, verificado por `tests/test_versoes_python.py` (Task R2.1) |
| 05-19 | Dependência `openai` declarada e nunca importada (clients usam `httpx`) | `pyproject.toml:18` | Baixa | **CORRIGIDO** — removida de `pyproject.toml`/`requirements.txt` (Task R2.1) |
```

---

### Task R2.2: CI bloqueante no backend (cobertura e mypy)

**Files:**
- Modify: `backend/pyproject.toml` (`[tool.coverage.*]`, `pytest-cov` no extra `dev`)
- Modify: `backend/requirements.txt` (`pytest-cov`)
- Modify: `.github/workflows/ci.yml` (job `backend`)
- Test: `backend/tests/test_ci_backend.py`

**Interfaces:**
- Produces: job `backend` que roda
  ```
  uv run pytest tests/ -q -p no:cacheprovider --cov=app --cov-report=term-missing
  uv run mypy app/ --ignore-missing-imports
  ```
  sem `|| true`, com `[tool.coverage.report] fail_under` aplicado via `--cov-fail-under` no workflow.

**Regra do número:** o threshold **não é inventado**. O Step 3 instrui a medir a cobertura real; o valor commitado é o medido arredondado **para baixo** (nunca acima do medido). A task R2.5 sobe o piso para 70 depois de remover o ORM morto. Um threshold acima do real quebraria o CI na hora e seria "verificação falsa" (C2).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ci_backend.py`:

```python
"""O CI do backend precisa bloquear regressao de teste, tipo e cobertura."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CI = (RAIZ / ".github/workflows/ci.yml").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((RAIZ / "backend/pyproject.toml").read_text(encoding="utf-8"))


def _job_backend() -> str:
    inicio = CI.index("  backend:")
    fim = CI.index("  frontend:")
    return CI[inicio:fim]


def test_pytest_roda_com_cobertura_e_threshold():
    job = _job_backend()

    assert "--cov=app" in job
    assert "--cov-fail-under=" in job


def test_mypy_nao_e_report_only():
    job = _job_backend()

    assert "mypy" in job
    assert "mypy app/ --ignore-missing-imports || true" not in job


def test_pytest_cov_e_dependencia_de_dev():
    dev = PYPROJECT["project"]["optional-dependencies"]["dev"]

    assert any(dep.startswith("pytest-cov") for dep in dev)
    assert "pytest-cov" in (RAIZ / "backend/requirements.txt").read_text(encoding="utf-8")


def test_cobertura_configurada_no_pyproject():
    report = PYPROJECT["tool"]["coverage"]["report"]

    assert report["fail_under"] >= 1
    assert report["show_missing"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_ci_backend.py -v`

Expected: FAIL — não há `--cov` no CI, `mypy ... || true` presente e `pytest-cov` ausente das dependências.

- [ ] **Step 3: Medir e implementar**

1. Acrescente `pytest-cov>=5.0.0` ao extra `dev` de `pyproject.toml` e ao `backend/requirements.txt`; rode `cd backend && uv lock && uv sync --extra dev`.
2. Meça:

```bash
cd backend && uv run pytest tests/ -q --cov=app --cov-report=term | tail -15
```

3. Anote o `TOTAL` (%). Use `FLOOR` = esse valor arredondado para baixo (ex.: 63.7% → `63`).

`backend/pyproject.toml`:

```toml
[tool.coverage.run]
source = ["app"]

[tool.coverage.report]
show_missing = true
fail_under = 60
```

(substitua `60` pelo `FLOOR` medido no passo 2)

`.github/workflows/ci.yml` — job `backend`, substituir as duas etapas:

```yaml
      - name: Type check (mypy)
        run: uv run mypy app/ --ignore-missing-imports

      - name: Testes (pytest + cobertura)
        run: |
          uv run pytest tests/ -q -p no:cacheprovider \
            --cov=app --cov-report=term-missing --cov-fail-under=60
```

(substitua `60` pelo mesmo `FLOOR`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_ci_backend.py -v`

Expected: PASS (4 testes).

- [ ] **Step 5: Rodar o pipeline local como o CI**

Run: `cd backend && uv run mypy app/ --ignore-missing-imports && uv run pytest tests/ -q --cov=app --cov-report=term-missing --cov-fail-under=60`

Expected: mypy sem erro (corrija os que aparecerem **na própria task** — são ajustes de anotação, não refactor) e pytest acima do piso.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/requirements.txt \
  .github/workflows/ci.yml backend/tests/test_ci_backend.py
git commit -m "ci(backend): cobertura e mypy bloqueiam o merge

- pytest roda com --cov=app e piso de cobertura medido (nao inventado)
- mypy deixa de ser report-only
- pytest-cov declarado nas dependencias de dev"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09 e 14)**

```
| 09-14 | CI: mypy e lint do frontend report-only; sem job de teste do frontend | `.github/workflows/ci.yml` | Média | **ABERTO (parcial)** — backend bloqueia mypy e cobertura (Task R2.2); frontend na Task R2.3 |
| 14-9 | CI sem threshold de cobertura; mypy e lint frontend report-only | `ci.yml` | Média | **ABERTO (parcial)** — `--cov-fail-under` e mypy bloqueante no backend (Task R2.2); frontend na R2.3 |
```

---

### Task R2.3: CI bloqueante no frontend (Vitest + cobertura + lint)

**Files:**
- Modify: `frontend/package.json` (`@vitest/coverage-v8`, scripts `test:coverage`)
- Modify: `frontend/vitest.config.ts` (thresholds de cobertura)
- Modify: `.github/workflows/ci.yml` (job `frontend`)
- Test: `frontend/src/test/ci.test.ts`

**Interfaces:**
- Produces: job `frontend` com `npm run test` (bloqueante), `npm run test:coverage` com thresholds e `npm run lint` bloqueante; `vitest.config.ts` com `coverage.thresholds`.

**Nota:** o harness Vitest **não** nasce aqui — ele é criado na Task F4.1, porque a C1 exige teste desde a primeira task de UI. Esta task só o torna obrigatório no CI e adiciona cobertura.

**Regra do número:** mesma regra da R2.2 — meça `npm run test:coverage` e commite o piso medido arredondado para baixo.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/test/ci.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(process.cwd(), "..");
const CI = readFileSync(join(RAIZ, ".github/workflows/ci.yml"), "utf8");
const CONFIG = readFileSync(join(process.cwd(), "vitest.config.ts"), "utf8");
const PACKAGE = JSON.parse(
  readFileSync(join(process.cwd(), "package.json"), "utf8")
) as { scripts: Record<string, string>; devDependencies: Record<string, string> };

function jobFrontend(): string {
  const inicio = CI.indexOf("  frontend:");
  const fim = CI.indexOf("  docker:");
  return CI.slice(inicio, fim);
}

describe("CI do frontend", () => {
  it("roda os testes de unidade", () => {
    expect(jobFrontend()).toContain("npm run test");
  });

  it("roda a cobertura", () => {
    expect(jobFrontend()).toContain("npm run test:coverage");
    expect(PACKAGE.scripts["test:coverage"]).toContain("coverage");
  });

  it("nao deixa o lint em report-only", () => {
    expect(jobFrontend()).toContain("npm run lint");
    expect(jobFrontend()).not.toContain("npm run lint || true");
  });

  it("exige cobertura minima no vitest", () => {
    expect(CONFIG).toContain("thresholds");
    expect(CONFIG).toMatch(/lines:\s*\d+/);
  });

  it("declara o provider de cobertura", () => {
    expect(PACKAGE.devDependencies["@vitest/coverage-v8"]).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/test/ci.test.ts`

Expected: FAIL — não há `test:coverage`, `thresholds`, `@vitest/coverage-v8` nem `npm run test` no CI.

- [ ] **Step 3: Medir e implementar**

1. `cd frontend && npm i -D @vitest/coverage-v8@^2.1.8`
2. Meça:

```bash
cd frontend && npx vitest run --coverage --coverage.reporter=text | tail -20
```

3. Use `FLOOR` = `lines` medido arredondado para baixo.

`frontend/package.json`:

```json
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
```

`frontend/vitest.config.ts` — dentro de `test`:

```ts
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/test/**", "src/**/*.test.{ts,tsx}", "src/**/*.d.ts"],
      thresholds: {
        lines: 60,
        functions: 60,
        branches: 60,
        statements: 60,
      },
    },
```

(substitua `60` pelos pisos medidos; `branches` pode ser menor se o medido for menor)

`.github/workflows/ci.yml` — job `frontend`, substituir as etapas finais:

```yaml
      - name: Lint
        run: npm run lint

      - name: Testes (vitest)
        run: npm run test

      - name: Cobertura
        run: npm run test:coverage

      - name: Build
        run: npm run build
```

> Se `npm run lint` falhar por regra preexistente, corrija **nesta task** (imports não usados, `useEffect` sem dependência) — é dívida de lint, não refactor de tela. Se o volume for grande, registre em `14-9` como aberto parcial com a lista, em vez de manter `|| true`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/test/ci.test.ts`

Expected: PASS (5 testes).

- [ ] **Step 5: Rodar o pipeline local como o CI**

Run: `cd frontend && npm run lint && npm run test && npm run test:coverage && npm run build`

Expected: verde nos quatro; `npm run test:coverage` imprime a tabela e não falha nos thresholds.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts \
  frontend/src/test/ci.test.ts .github/workflows/ci.yml
git commit -m "ci(frontend): vitest, cobertura e lint bloqueiam o merge

- job frontend roda testes, cobertura e lint sem report-only
- thresholds de cobertura medidos no vitest (nao inventados)
- teste garante que o pipeline continua bloqueante"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09, 14, 07)**

```
| 09-14 | CI: mypy e lint do frontend report-only; sem job de teste do frontend | `.github/workflows/ci.yml` | Média | **CORRIGIDO** — jobs backend (R2.2) e frontend (R2.3) rodam lint, tipos, testes e cobertura bloqueantes |
| 14-6 | Frontend sem infraestrutura de teste (sem `test` script, sem Vitest/Playwright) | `frontend/package.json` | **Alta** | **CORRIGIDO** — Vitest/jsdom/Testing Library desde a Task F4.1; CI bloqueante e cobertura na Task R2.3 |
| 14-9 | CI sem threshold de cobertura; mypy e lint frontend report-only | `ci.yml` | Média | **CORRIGIDO** — `--cov-fail-under` (R2.2) e thresholds do Vitest (R2.3) |
```

---

### Task R2.4: Backup de Appwrite/Qdrant/n8n com agendamento

**Files:**
- Modify: `scripts/backup.sh`
- Create: `infra/systemd/emsoft-backup.service`
- Create: `infra/systemd/emsoft-backup.timer`
- Test: `backend/tests/test_backup_script.py`

**Interfaces:**
- Produces: `backup.sh` que gera, com data/hora,
  - `postgres_<DATA>.sql.gz` — `pg_dump` do container `postgres` (cobre Evolution API e n8n se usarem o mesmo banco);
  - `appwrite-mariadb_<DATA>.tar.gz` e `appwrite-uploads_<DATA>.tar.gz` — volumes nomeados do Appwrite;
  - `qdrant_<DATA>.tar.gz` — volume `qdrant-data` (o bind mount `docker-data/qdrant` do script atual **não existe** em prod);
  - `n8n_<DATA>.tar.gz` — volume `n8n-data`;
  - retenção configurável (`RETENCAO_DIAS`, padrão 14);
  - verificação de que cada arquivo gerado é legível (`gzip -t` / `tar tzf`).
- `infra/systemd/emsoft-backup.{service,timer}` — execução diária às 03:00 com `Persistent=true`.

**Alternativa descartada:** backup lógico do Appwrite via API (`databases.list_documents` de todas as coleções). É mais portátil, mas exigiria manter um script que conhece todo o schema e falha silenciosamente em coleção nova; o volume do MariaDB é atômico e não depende de API key. O preço (restore precisa da mesma versão do Appwrite) está documentado no cabeçalho do script — **não** documentar restore é o que transforma backup em teatro.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_backup_script.py`:

```python
"""Backup cobre as stores reais da pilha de producao."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = (RAIZ / "scripts/backup.sh").read_text(encoding="utf-8")
SERVICO = (RAIZ / "infra/systemd/emsoft-backup.service").read_text(encoding="utf-8")
TIMER = (RAIZ / "infra/systemd/emsoft-backup.timer").read_text(encoding="utf-8")


def test_backup_do_postgres_continua():
    assert "pg_dump" in SCRIPT
    assert "postgres" in SCRIPT


def test_backup_usa_volumes_nomeados_de_producao():
    for volume in ("appwrite-mariadb", "appwrite-uploads", "qdrant-data", "n8n-data"):
        assert volume in SCRIPT, f"volume {volume} nao e copiado"


def test_nao_usa_bind_mount_inexistente():
    assert "docker-data/qdrant" not in SCRIPT


def test_copia_volume_com_container_efemero():
    assert "docker run --rm" in SCRIPT
    assert "/backup" in SCRIPT


def test_retencao_configuravel_e_aplicada():
    assert "RETENCAO_DIAS" in SCRIPT
    assert "-mtime" in SCRIPT


def test_valida_os_arquivos_gerados():
    assert "gzip -t" in SCRIPT
    assert "tar tzf" in SCRIPT


def test_systemd_executa_o_script_do_repositorio():
    assert "ExecStart=" in SERVICO
    assert "scripts/backup.sh" in SERVICO
    assert "After=docker.service" in SERVICO


def test_timer_roda_todo_dia_as_tres():
    assert "OnCalendar=*-*-* 03:00:00" in TIMER
    assert "Persistent=true" in TIMER
    assert "WantedBy=timers.target" in TIMER
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_backup_script.py -v`

Expected: FAIL — `infra/systemd/` não existe, o script usa `docker-data/qdrant` e não copia volume nenhum.

- [ ] **Step 3: Write minimal implementation**

Substitua `scripts/backup.sh` por:

```bash
#!/usr/bin/env bash
# Backup da pilha de producao.
#
# Restore: os volumes do Appwrite devem ser restaurados na MESMA versao da imagem
# (infra/appwrite/docker-compose.yml) e com o stack parado. O dump do Postgres usa
# pg_restore/psql na mesma major version (16).
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENCAO_DIAS="${RETENCAO_DIAS:-14}"
COMPOSE_FILE="infra/docker-compose.prod.yml"
DATA=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
ABSOLUTO="$(cd "$BACKUP_DIR" && pwd)"

echo "=== EMSoft Support - Backup ($DATA) ==="

echo "PostgreSQL..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U emsoft emsoft > "$BACKUP_DIR/postgres_$DATA.sql"
gzip -t < /dev/null 2>/dev/null || true
gzip -f "$BACKUP_DIR/postgres_$DATA.sql"
gzip -t "$BACKUP_DIR/postgres_$DATA.sql.gz"

copia_volume() {
  local volume="$1"
  local nome="$2"
  echo "Volume $volume..."
  docker run --rm \
    -v "${volume}:/origem:ro" \
    -v "${ABSOLUTO}:/backup" \
    alpine:3.20 \
    tar czf "/backup/${nome}_${DATA}.tar.gz" -C /origem .
  tar tzf "$BACKUP_DIR/${nome}_${DATA}.tar.gz" > /dev/null
}

copia_volume appwrite-mariadb appwrite-mariadb
copia_volume appwrite-uploads appwrite-uploads
copia_volume qdrant-data qdrant
copia_volume n8n-data n8n

echo "Retencao de $RETENCAO_DIAS dias..."
find "$BACKUP_DIR" -type f -mtime "+$RETENCAO_DIAS" -delete

echo "=== Backup complete: $BACKUP_DIR ==="
ls -lh "$BACKUP_DIR"/*"$DATA"*
```

> A linha `gzip -t < /dev/null || true` existe só para o teste de contrato ser explícito; se preferir, remova-a e mantenha apenas o `gzip -t` sobre o arquivo gerado (o teste casa com o `gzip -t` do arquivo real).

`infra/systemd/emsoft-backup.service`:

```ini
[Unit]
Description=Backup da stack EMSoft Support
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/emsoft-support
Environment=BACKUP_DIR=/opt/emsoft-support/backups
ExecStart=/opt/emsoft-support/scripts/backup.sh
```

`infra/systemd/emsoft-backup.timer`:

```ini
[Unit]
Description=Backup diario da stack EMSoft Support

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=600

[Install]
WantedBy=timers.target
```

Instalação (documentar no cabeçalho do serviço e no `docs/specs/09` quando o Registro for atualizado):

```bash
sudo cp infra/systemd/emsoft-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now emsoft-backup.timer
systemctl list-timers emsoft-backup.timer
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_backup_script.py -v`

Expected: PASS (8 testes).

- [ ] **Step 5: Rodar o script em ambiente de teste (sem produção)**

Run: `cd /tmp && BACKUP_DIR=/tmp/backups-teste bash <repo>/scripts/backup.sh`

Expected: com a stack de produção fora, o script falha no primeiro comando (`exec -T postgres`) — isso é **correto** (não gera backup vazio e não mente). Confirme que o erro é do docker/compose e não de sintaxe (`bash -n scripts/backup.sh` deve passar).

Run: `bash -n scripts/backup.sh`

- [ ] **Step 6: Commit**

```bash
git add scripts/backup.sh infra/systemd/emsoft-backup.service \
  infra/systemd/emsoft-backup.timer backend/tests/test_backup_script.py
git commit -m "feat(infra): backup de appwrite, qdrant e n8n com timer

- volumes nomeados de producao (appwrite-mariadb, uploads, qdrant, n8n)
- bind mount inexistente docker-data/qdrant removido
- retencao configuravel e verificacao de integridade dos arquivos
- timer systemd diario as 03:00 com Persistent"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09, 00, 08)**

```
| 09-5 | Backup Qdrant usa bind mount divergente do volume named de prod | `scripts/backup.sh` | **Alta** | **CORRIGIDO** — cópia do volume `qdrant-data` via container efêmero (Task R2.4) |
| 09-6 | Sem backup de Appwrite/n8n/evolution-db; bloco Supabase remanescente | `scripts/backup.sh` | **Alta** | **CORRIGIDO** — volumes `appwrite-mariadb`, `appwrite-uploads`, `n8n-data`; Postgres cobre Evolution (Task R2.4) |
| 09-7 | `backup.sh` não é agendado | `scripts/` | **Alta** | **CORRIGIDO** — `infra/systemd/emsoft-backup.{service,timer}` (diário, `Persistent=true`) |
| 00-7 | Backup cobre só Postgres/Supabase; MinIO órfão e backup do Qdrant nunca dispara em prod | `scripts/backup.sh` | **Alta** | **CORRIGIDO** — mesma evidência da Task R2.4 |
```

---

### Task R2.5: Fim do drift Alembic/Postgres (ORM legado fora)

**Files:**
- Create: `backend/app/models/enums.py`
- Modify: `backend/app/models/{chat,mensagem,ia_diagnostico,knowledge_base,atendente,__init__}.py` (só reexportam enums)
- Delete: `backend/app/models/{cliente,tag}.py`, `backend/app/core/database.py`, `backend/alembic/`, `scripts/migrate.sh`, `scripts/seed_knowledge_base.py`
- Modify: `backend/app/core/config.py` (remover `database_url`, `database_url_prod`, `active_database_url`)
- Modify: `scripts/seed_qdrant.py` (lê do Appwrite via `Repositories`)
- Modify: `scripts/seed.sh` (não chama mais o seed SQLAlchemy nem `migrate.sh`)
- Modify: `backend/pyproject.toml`, `backend/requirements.txt` (remover `sqlalchemy`, `alembic`, `asyncpg`; `aiosqlite` do extra dev)
- Test: `backend/tests/test_remocao_orm.py`

**Interfaces:**
- Produces:
  - `app/models/enums.py` com todos os `StrEnum` (`StatusChat`, `PrioridadeChat`, `StatusIA`, `CategoriaConhecimento`, `RemetenteMensagem`, `TipoMensagem`, `PerfilAtendente`)
  - `app/models/chat.py` etc. reexportam (`from app.models.enums import StatusChat  # noqa: F401`) — os **37** pontos de import em **21** arquivos continuam funcionando
  - `scripts/seed_qdrant.coletar_artigos(repos) -> list[dict]` — artigos ativos vindos de `repos.knowledge_bases`
  - `[tool.coverage.report] fail_under = 70` (ratchet depois da remoção do código morto)

**Regra:** esta task **não** muda contrato de API nem de schema. O que sai é só o caminho de dados que a plataforma não usa: nada em `app/api`, `app/services` ou `app/appwrite` importa as classes ORM (verificado: só `models/__init__.py` as referenciava). Rode `grep -rn "core.database" backend scripts` antes de apagar — se aparecer algo novo, o mapa da task está incompleto e a task para.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_remocao_orm.py`:

```python
"""O caminho PostgreSQL/ORM legado sai do codigo e das dependencias."""

import importlib.util
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MODELS = RAIZ / "backend/app/models"
PYPROJECT = tomllib.loads((RAIZ / "backend/pyproject.toml").read_text(encoding="utf-8"))
REQUIREMENTS = (RAIZ / "backend/requirements.txt").read_text(encoding="utf-8")


def _carregar_seed_qdrant():
    espec = importlib.util.spec_from_file_location(
        "seed_qdrant", RAIZ / "scripts/seed_qdrant.py"
    )
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def test_enums_ficam_importaveis_pelo_caminho_antigo():
    from app.models.chat import PrioridadeChat, StatusChat
    from app.models.enums import StatusChat as StatusCentral

    assert StatusChat is StatusCentral
    assert PrioridadeChat("urgente").value == "urgente"


def test_models_nao_importam_sqlalchemy():
    infratores = [
        arquivo.name
        for arquivo in MODELS.glob("*.py")
        if "sqlalchemy" in arquivo.read_text(encoding="utf-8")
    ]

    assert infratores == []


@pytest.mark.parametrize(
    "caminho",
    [
        "backend/alembic",
        "backend/app/core/database.py",
        "scripts/migrate.sh",
        "scripts/seed_knowledge_base.py",
        "backend/app/models/cliente.py",
        "backend/app/models/tag.py",
    ],
)
def test_caminho_legado_removido(caminho: str):
    assert not (RAIZ / caminho).exists(), f"{caminho} deveria ter sido removido"


def test_dependencias_sem_postgres():
    deps = PYPROJECT["project"]["dependencies"]

    assert not [d for d in deps if d.startswith(("sqlalchemy", "alembic", "asyncpg"))]
    for pacote in ("sqlalchemy", "alembic", "asyncpg"):
        assert pacote not in REQUIREMENTS


def test_config_sem_database_url():
    from app.core.config import Settings

    config = Settings(_env_file=None)

    assert not hasattr(config, "active_database_url")


@pytest.mark.asyncio
async def test_seed_qdrant_le_do_appwrite(fake_repos):
    await fake_repos.knowledge_bases.create(
        {"titulo": "Erro de NF-e", "conteudo": "passo a passo", "ativo": True}
    )
    await fake_repos.knowledge_bases.create(
        {"titulo": "Antigo", "conteudo": "obsoleto", "ativo": False}
    )

    artigos = await _carregar_seed_qdrant().coletar_artigos(fake_repos)

    assert [artigo["titulo"] for artigo in artigos] == ["Erro de NF-e"]


def test_cobertura_sobe_para_70():
    assert PYPROJECT["tool"]["coverage"]["report"]["fail_under"] == 70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_remocao_orm.py -v`

Expected: FAIL — `app.models.enums` inexistente, `sqlalchemy` presente nos modelos, `alembic/` existente, `coletar_artigos` ausente.

- [ ] **Step 3: Write minimal implementation**

1. `backend/app/models/enums.py`:

```python
"""Enums de dominio, sem dependencia de ORM.

Vivem aqui (e nao em cada modulo de modelo) porque o ORM SQLAlchemy foi removido:
os modulos de modelo apenas reexportam para preservar os imports historicos.
"""

import enum


class StatusChat(enum.StrEnum):
    novo = "NOVO"
    ia_analisando = "IA_ANALISANDO"
    aguardando_cliente = "AGUARDANDO_CLIENTE"
    aguardando_humano_com_solucao = "AGUARDANDO_HUMANO_COM_SOLUCAO"
    aguardando_humano_sem_solucao = "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    em_atendimento = "EM_ATENDIMENTO"
    resolvido = "RESOLVIDO"
    encerrado = "ENCERRADO"


class PrioridadeChat(enum.StrEnum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class StatusIA(enum.StrEnum):
    resolvido_pela_ia = "RESOLVIDO_PELA_IA"
    transferir_com_solucao = "TRANSFERIR_COM_SOLUCAO"
    transferir_sem_solucao = "TRANSFERIR_SEM_SOLUCAO"


class CategoriaConhecimento(enum.StrEnum):
    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"


class RemetenteMensagem(enum.StrEnum):
    cliente = "cliente"
    ia = "ia"
    atendente = "atendente"
    sistema = "sistema"


class TipoMensagem(enum.StrEnum):
    texto = "texto"
    audio = "audio"
    documento = "documento"
    imagem = "imagem"


class PerfilAtendente(enum.StrEnum):
    admin = "admin"
    supervisor = "supervisor"
    atendente = "atendente"
```

> Os valores acima são o estado **final** (pós-F1.1: `CategoriaConhecimento` já tem `multiempresa`). O passo é **mover**, não redefinir — confira cada valor contra o arquivo original imediatamente antes de apagá-lo. Se algum membro mudar de valor, `tests/test_schemas.py` e o schema Appwrite quebram, o que é o sinal desejado. **Não** mova `Intencao`/`CategoriaERP` para cá: elas já vivem em `app/models/departamento.py` desde a F1.1 e permanecem lá.

2. Cada `backend/app/models/<arquivo>.py` fica só com a reexportação (exemplo para `chat.py`):

```python
"""Reexportacao historica dos enums de chat (ORM removido na Task R2.5)."""

from app.models.enums import PrioridadeChat, StatusChat

__all__ = ["PrioridadeChat", "StatusChat"]
```

3. `backend/app/models/__init__.py`:

```python
"""Enums de dominio reexportados (sem ORM)."""

from app.models.enums import (
    CategoriaConhecimento,
    PerfilAtendente,
    PrioridadeChat,
    RemetenteMensagem,
    StatusChat,
    StatusIA,
    TipoMensagem,
)

__all__ = [
    "CategoriaConhecimento",
    "PerfilAtendente",
    "PrioridadeChat",
    "RemetenteMensagem",
    "StatusChat",
    "StatusIA",
    "TipoMensagem",
]
```

4. Apagar os caminhos listados em **Files** (Delete) e rodar:

```bash
cd /media/emsoft/VMS12/projetos/chatbot-ia && grep -rn "core.database\|models.cliente\|models.tag" backend scripts || echo "sem referencias"
```

5. `scripts/seed_qdrant.py` — trocar o bloco SQLAlchemy por:

```python
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx

from app.appwrite.repositories import Repositories
from app.core.appwrite import build_appwrite_client, build_appwrite_databases
from app.core.config import settings
from app.services.qdrant_service import ensure_collection, upsert_article

OLLAMA_EMBED_URL = f"{settings.ollama_base_url}/api/embeddings"
EMBED_MODEL = settings.ollama_embed_model


async def coletar_artigos(repos) -> list[dict]:
    return [artigo for artigo in await repos.knowledge_bases.list_all() if artigo.get("ativo")]


async def generate_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text[:8000]}
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def seed() -> None:
    databases = build_appwrite_databases(build_appwrite_client())
    artigos = await coletar_artigos(Repositories(databases))

    await ensure_collection()

    if not artigos:
        print("Nenhum artigo ativo encontrado na base de conhecimento.")
        return

    print(f"Gerando embeddings para {len(artigos)} artigos...")
    for artigo in artigos:
        texto = f"{artigo['titulo']}\n\n{artigo.get('conteudo') or ''}"
        embedding = await generate_embedding(texto)
        await upsert_article(
            article_id=artigo["id"],
            titulo=artigo["titulo"],
            conteudo=artigo.get("conteudo"),
            categoria=artigo["categoria"],
            embedding=embedding,
        )


if __name__ == "__main__":
    asyncio.run(seed())
```

6. `scripts/seed.sh` — hoje ele já chama **só** `seed_appwrite.py`; não há `alembic`/`seed_knowledge_base.py` nele. Confirme com `grep -n "alembic\|seed_knowledge_base" scripts/seed.sh` (deve sair vazio) e, opcionalmente, acrescente `seed_knowledge_base_appwrite.py` e `seed_qdrant.py` ao final para o seed ficar completo em um comando.

7. `backend/app/core/config.py` — remover `database_url`, `database_url_prod`, `active_database_url` e o import de `_INSECURE_DEFAULT_SECRET` se ficar sem uso.

8. `backend/pyproject.toml` / `backend/requirements.txt` — remover `sqlalchemy[asyncio]`, `alembic`, `asyncpg` (e `aiosqlite` do extra `dev`); subir `fail_under` para `70`; rodar `uv lock && uv sync --extra dev`.

9. `backend/Dockerfile` — o `HEALTHCHECK` continua em `/health`; se preferir readiness, troque para `/health/ready` (opcional, não exigido pelos testes).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_remocao_orm.py -v`

Expected: PASS (10 testes, contando os parametrizados).

- [ ] **Step 5: Rodar a suíte completa e o pipeline**

Run: `cd backend && uv run pytest tests/ -q --cov=app --cov-fail-under=70 && uv run ruff check app tests && uv run mypy app/ --ignore-missing-imports`

Expected: verde; `tests/test_schemas.py` e `tests/test_chat_service.py` continuam passando (importam enums pelo caminho antigo).

Run: `bash -n scripts/seed.sh && bash -n scripts/backup.sh`

- [ ] **Step 6: Commit**

```bash
git add -A backend/app/models backend/app/core/config.py backend/pyproject.toml \
  backend/uv.lock backend/requirements.txt scripts/seed_qdrant.py scripts/seed.sh \
  backend/tests/test_remocao_orm.py
git rm -r backend/alembic backend/app/core/database.py scripts/migrate.sh \
  scripts/seed_knowledge_base.py backend/app/models/cliente.py backend/app/models/tag.py
git commit -m "refactor(backend): remove o caminho postgres/alembic legado

- enums centralizados em app/models/enums.py e reexportados pelos modulos
- ORM, alembic, migrate.sh e seed SQLAlchemy removidos
- seed_qdrant le artigos do Appwrite via Repositories
- sqlalchemy/alembic/asyncpg fora das dependencias; cobertura sobe para 70"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 02, 08, 14)**

```
| 02-11 | `backend/alembic/`, `app/models/*.py` (ORM) e `scripts/migrate.sh` apontam para PostgreSQL, que não é a fonte atual | `backend/alembic/`; `scripts/migrate.sh` | **Alta** | **CORRIGIDO** — ORM/Alembic/migrate removidos; enums em `app/models/enums.py` (Task R2.5) |
| 02-14 | `scripts/seed_qdrant.py` lê do PostgreSQL e usa id inteiro como ponto Qdrant | `scripts/seed_qdrant.py` | **Alta** | **CORRIGIDO** — `coletar_artigos(repos)` lê do Appwrite e usa o `id` ULID (Task R2.5) |
| 09-12 | Alembic/Postgres híbrido com runtime em Appwrite | `alembic/env.py`; `seed_qdrant.py` | Média | **CORRIGIDO** — mesma remoção de ORM/Alembic/seed PostgreSQL da Task R2.5 (fecha junto de 02-11/02-14) |
| 08-7 | `DATABASE_URL` default com credenciais em claro | `core/config.py:10` | Baixa | **CORRIGIDO** — campo `database_url` removido junto do caminho Postgres (Task R2.5) |
| 14-9 | CI sem threshold de cobertura | `ci.yml` | Média | **CORRIGIDO** — piso elevado para 70% após remoção do código morto (Task R2.5) |
```

---

### Task R2.6: Credenciais fora do compose e remoção do MinIO órfão

**Files:**
- Modify: `infra/docker-compose.prod.yml` (Postgres/Evolution com `${POSTGRES_PASSWORD}`, remover `minio` e `MINIO_*`)
- Modify: `infra/.env.example` (`POSTGRES_PASSWORD`)
- Test: `backend/tests/test_credenciais_compose.py`

**Interfaces:**
- Produces: compose prod sem senha literal e sem serviço/volume MinIO; `.env.example` documentando `POSTGRES_PASSWORD`.

**Decisão sobre o MinIO:** o código nunca referenciou MinIO (o backend não tem campo `minio_*` em `Settings`; o compose passava variáveis que o Pydantic ignorava). Manter um serviço sem consumidor custa memória, superfície e um volume a fazer backup. Ele sai; se upload de mídia voltar ao escopo, entra junto do gap de mídia (00-11) com o código que o consome.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_credenciais_compose.py`:

```python
"""Compose de producao sem segredo literal e sem servico orfao."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = (RAIZ / "infra/docker-compose.prod.yml").read_text(encoding="utf-8")
EXEMPLO = (RAIZ / "infra/.env.example").read_text(encoding="utf-8")


def test_senha_do_postgres_vem_do_env():
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}" in COMPOSE
    assert "POSTGRES_PASSWORD: emsoft" not in COMPOSE


def test_uri_da_evolution_usa_a_senha_do_env():
    assert "postgresql://emsoft:${POSTGRES_PASSWORD}@postgres:5432/emsoft" in COMPOSE
    assert "emsoft:emsoft@" not in COMPOSE


def test_minio_orfao_removido():
    assert "minio" not in COMPOSE.lower()
    assert "MINIO_" not in COMPOSE


def test_env_example_documenta_a_senha():
    assert "POSTGRES_PASSWORD=" in EXEMPLO


def test_backup_nao_depende_de_minio():
    script = (RAIZ / "scripts/backup.sh").read_text(encoding="utf-8")

    assert "minio" not in script.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_credenciais_compose.py -v`

Expected: FAIL — `POSTGRES_PASSWORD: emsoft`, `emsoft:emsoft@` e o bloco `minio` presentes.

- [ ] **Step 3: Write minimal implementation**

Em `infra/docker-compose.prod.yml`:

```yaml
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: emsoft
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: emsoft
```

```yaml
      DATABASE_CONNECTION_URI: postgresql://emsoft:${POSTGRES_PASSWORD}@postgres:5432/emsoft
```

Remover do `backend.environment`:

```yaml
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin}
```

Remover o serviço `minio:` inteiro e a linha `minio-data:` de `volumes:`.

Em `infra/.env.example`:

```dotenv
# === PostgreSQL (Evolution API e n8n) ===
# Usada pelo compose de produção. Gere uma senha forte e não a versione.
POSTGRES_PASSWORD=troque-esta-senha
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_credenciais_compose.py -v`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check app tests`

Expected: verde, incluindo `tests/test_compose_prod.py` (R0.3) e `tests/test_env_example.py` (R0.5).

- [ ] **Step 6: Commit**

```bash
git add infra/docker-compose.prod.yml infra/.env.example \
  backend/tests/test_credenciais_compose.py
git commit -m "fix(infra): senha do postgres vem do env e minio orfao sai

- POSTGRES_PASSWORD obrigatoria no compose e na URI da Evolution
- servico/volume MinIO removidos (nenhum codigo os consumia)
- .env.example documenta a senha com placeholder"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 09 e 08)**

```
| 09-8 | Senha do Postgres em claro no compose/string da Evolution | `infra/docker-compose.prod.yml` | Média | **CORRIGIDO** — `${POSTGRES_PASSWORD}` no serviço e na URI (Task R2.6) |
| 09-3 | MinIO órfão no compose prod sem referência no código | `infra/docker-compose.prod.yml` | Baixa | **CORRIGIDO** — serviço e volume removidos (Task R2.6) |
```

## Gate R2 — critério de saída

- [ ] `cd backend && uv run pytest tests/ -q --cov=app --cov-fail-under=70 && uv run ruff check app tests && uv run mypy app/ --ignore-missing-imports` verde.
- [ ] `cd frontend && npm run lint && npm run test && npm run test:coverage && npm run build` verde.
- [ ] `grep -rn "sqlalchemy\|alembic" backend/app backend/pyproject.toml backend/requirements.txt` não retorna nada.
- [ ] `bash -n scripts/backup.sh scripts/seed.sh scripts/start-prod.sh` sem erro; `systemctl list-timers emsoft-backup.timer` mostra a próxima execução no host de produção.
- [ ] Nenhum segredo literal em `infra/docker-compose*.yml` (senha, API key, encryption key).
- [ ] Registros de Gaps atualizados: 09-3, 09-5, 09-6, 09-7, 09-8, 09-9, 09-14, 09-16, 00-7, 00-10, 00-16, 02-11, 02-14, 05-14, 05-19, 08-1, 08-3, 08-5, 08-7, 08-9, 08-12, 09-1, 09-2, 09-4, 09-15, 12-6, 14-6, 14-9.

---

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Threshold de cobertura inventado quebra o CI na hora | R2.2/R2.3 exigem **medir** antes; o número commitado é o medido arredondado para baixo, com ratchet explícito na R2.5 |
| Rede `appwrite` externa não existir no primeiro deploy | `start-prod.sh` sobe a pilha do Appwrite antes (R0.4) e falha com mensagem clara se o compose dela não subir |
| `/health/ready` derrubar tráfego por sonda lenta | Sondas têm timeout de 2s e rodam em paralelo; o readiness cobre só `appwrite` e `schema` — Ollama/Qdrant **não** são sondados de propósito (o LLM pode estar lento sem o inbox parar) |
| Remoção do ORM quebrar import esquecido | `grep -rn "core.database\|models.cliente\|models.tag"` no Step 3 e reexportação dos enums pelos módulos antigos |
| Backup do volume MariaDB exigir a mesma versão no restore | Documentado no cabeçalho do script e no Registro de Gaps da spec 09 |
| `npm run lint` bloquear por dívida preexistente | R2.3 autoriza corrigir apenas achados de lint na própria task; se o volume for grande, `14-9` fica ABERTO (parcial) com a lista |






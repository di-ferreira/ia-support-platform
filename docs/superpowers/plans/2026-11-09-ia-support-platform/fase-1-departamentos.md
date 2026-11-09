# Fase 1 — Departamentos, Migração de Setor e Visibilidade

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a entidade `departamentos` com CRUD, as `regras_roteamento` como fonte do roteamento determinístico, o vínculo `departamento_id` em atendentes e chats, o seed dos seis departamentos iniciais, a migração do `setor`/`setor_alvo` legado e a visibilidade por departamento.

**Architecture:** Coleções declarativas em `backend/app/appwrite/schema.py` (fonte do schema Appwrite e dos `FakeStore` de teste), repositórios finos sobre `BaseRepository`, um `DepartamentoService` que concentra as regras (unicidade de `codigo`, bloqueio de desativação com vínculos), rotas em arquivo próprio `api/routes/departamentos.py`. A lógica de seed e de migração vive em `services/` (testável sem rede); os scripts em `scripts/` são wrappers finos.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, Appwrite SDK (chamado só em produção; testes usam fakes), pytest + pytest-asyncio.

**Specs:** `docs/specs/02-data-model.md` (§Novas coleções, §Migração de setor legado, §Unicidade, concorrência e bootstrap), `docs/specs/03-api-contract.md` (§Novos endpoints de departamento), `docs/specs/10-departamentos-e-roteamento.md`, `docs/specs/04-rbac-matrix.md`, `docs/superpowers/specs/2026-11-09-plano-implementacao-design.md` §5 e §6.

## Global Constraints

Vale `README.md` §Global Constraints (C1–C12). Em especial nesta fase: **C6** (`setor`/`setor_alvo` não são apagados) e **C4** (gap atualizado na mesma task).

## Rastreio gap → task

| Gap | Task | Evidência que fecha |
|---|---|---|
| 02-1 | F1.1 | `CATEGORIA_CONHECIMENTO` derivado de `CategoriaConhecimento` (inclui `multiempresa`); teste de paridade com `CategoriaERP` |
| 02-2 | F1.1 | `CategoriaConhecimento.multiempresa` |
| 05-17 | F1.1 | idem 02-1/02-2 (mesma causa) |
| 01-10 | F1.1 | `Intencao` modelada em `app/models/departamento.py` |
| 00-13 | F1.2, F2.4, F3.4 | coleções + roteamento + cenários |
| 10-1 | F1.2, F1.3 | coleção `departamentos` + `DepartamentoRepository` |
| 10-2 | F1.2, F1.3 | coleção `regras_roteamento` + `RegraRoteamentoRepository` |
| 02-17 | F1.2 (parcial) | `departamentos`/`regras_roteamento` criadas; `integracao_chamados`/`integration_outbox` ficam para a Fase 5 |
| 10-3 | F1.2, F1.8 | `atendentes.departamento_id` |
| 10-4 | F1.2, F1.8 | `chats.departamento_id` |
| 02-18 | F1.2 | idem 10-3/10-4 |
| 10-5 | F1.4, F1.5 | service + rotas |
| 03-19 | F1.5 (parcial) | `/departamentos*` existem |
| 02-12 | F1.4 | unicidade de `codigo` centralizada no service + teste de duplicidade |
| 10-9 | F1.6 | seed idempotente |
| 10-10 | F1.7 | migração com relatório de órfãos |
| 02-4 | F1.7, F1.8 | legado preservado e lido só como fallback |
| 01-9 | F1.8, F1.9 | departamento na máquina de estados e na visibilidade |
| 04-10 | F1.9 | escopo por departamento em `listar` |
| 04-1 | F1.9 | dashboard com filtro de visibilidade |
| 03-1 | F1.9 | idem 04-1 |
| 02-15 | F1.9 | `clientes.get` fora do loop |
| 04-2 | F1.10 | posse em `/chats/{id}`, `/chats/{id}/mensagens`, `/clientes/{id}` |
| 03-2 | F1.10 | idem 04-2 |
| 02-10 | F1.1 (passo manual) + R1.4 (health) | bootstrap não propaga enum; ver nota em F1.1 |

**Nota obrigatória de F1.1:** o bootstrap aditivo não propaga mudança de enum (gap **02-10**). Adicionar `multiempresa` a `CATEGORIA_CONHECIMENTO` exige **atualizar o enum manualmente no Appwrite** antes do deploy (spec 02 §Unicidade, concorrência e bootstrap). O código e os testes passam; o ambiente de produção precisa do passo manual documentado no commit. A metade "health degradado" do gap 02-10 fecha na Task R1.4; a propagação automática de enum **continua ABERTA** (o gap fica ABERTO parcial até o bootstrap ganhar atualização de enum).

---

### Task F0.1: Baseline da suíte de testes

**Files:**
- Create: `backend/tests/BASELINE.md`

**Interfaces:**
- Consumes: nada.
- Produces: registro do estado da suíte (contagem por arquivo, falhas preexistentes) que todas as tasks seguintes usam como referência de "isto já falhava antes".

Esta é a única task de medição do plano: o "teste" é a própria suíte. Se houver falha preexistente, ela é registrada — não corrigida aqui.

- [ ] **Step 1: Rodar a suíte e capturar o estado atual**

Run: `cd backend && pytest tests/ -q -p no:cacheprovider 2>&1 | tee /tmp/opencode/baseline.txt`
Expected: linha final `N passed` (sem `failed`). Se houver falhas, elas são o baseline — anote o nome de cada uma.

- [ ] **Step 2: Capturar a contagem por arquivo**

Run: `cd backend && pytest tests/ -q --collect-only 2>/dev/null | grep '::' | cut -d: -f1 | sort | uniq -c | sort -rn`
Expected: uma linha por arquivo de teste com a contagem de casos.

- [ ] **Step 3: Escrever o baseline**

Create `backend/tests/BASELINE.md`:

```markdown
# Baseline da suíte — 2026-11-09 (antes da Fase 1)

Comando: `pytest tests/ -q -p no:cacheprovider`

## Resultado

- Total: <N> passed, <M> failed, <K> skipped
- Duração: <Xs>

## Contagem por arquivo

| Arquivo | Casos |
|---|---:|
<cole aqui a saída do Step 2>

## Falhas preexistentes

<liste cada `ARQUIVO::teste` que falhou, ou escreva "nenhuma">

## Interpretação

Qualquer falha listada acima **não** é regressão de uma task do plano.
Uma task que introduza falha nova deve ser corrigida antes do commit.
```

- [ ] **Step 4: Confirmar que a suíte continua verde (ou idêntica ao baseline)**

Run: `cd backend && pytest tests/ -q -p no:cacheprovider`
Expected: o mesmo `N passed` do Step 1.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/BASELINE.md
git commit -m "test(baseline): registra estado da suíte antes da fase 1"
```

---

### Task F1.1: Enums de intenção e categoria ERP; `multiempresa` na base de conhecimento

**Files:**
- Create: `backend/app/models/departamento.py`
- Modify: `backend/app/models/knowledge_base.py:8-13` (`CategoriaConhecimento`)
- Modify: `backend/app/appwrite/schema.py:52` (`CATEGORIA_CONHECIMENTO`) e bloco de listas
- Test: `backend/tests/test_departamento_models.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `app.models.departamento.Intencao` — `StrEnum` com 9 valores (`problema_tecnico`, `duvida_uso_erp`, `solicitacao_financeira`, `solicitacao_comercial`, `solicitacao_administrativa`, `implantacao_treinamento`, `solicitacao_humano`, `duvida_geral`, `intencao_desconhecida`)
  - `app.models.departamento.CategoriaERP` — `StrEnum` com 6 valores (`fiscal`, `estoque`, `compras`, `vendas`, `financeiro`, `multiempresa`)
  - `app.appwrite.schema.INTENCAO`, `CATEGORIA_ERP`, `CATEGORIA_CONHECIMENTO` — listas de strings derivadas dos enums

**Decisão de modelagem (aprovada):** `outro` **não** é categoria em lugar nenhum; o classificador devolve `categoria_erp=null`. `multiempresa` entra como categoria real.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_models.py`:

```python
"""Taxonomia de intenção e categoria ERP deve espelhar docs/specs/05 e 02."""

from app.appwrite import schema
from app.models.departamento import CategoriaERP, Intencao
from app.models.knowledge_base import CategoriaConhecimento


def test_intencao_tem_as_nove_intencoes_da_spec_05():
    assert {i.value for i in Intencao} == {
        "problema_tecnico",
        "duvida_uso_erp",
        "solicitacao_financeira",
        "solicitacao_comercial",
        "solicitacao_administrativa",
        "implantacao_treinamento",
        "solicitacao_humano",
        "duvida_geral",
        "intencao_desconhecida",
    }


def test_categoria_erp_tem_seis_modulos_e_nao_tem_outro():
    assert {c.value for c in CategoriaERP} == {
        "fiscal",
        "estoque",
        "compras",
        "vendas",
        "financeiro",
        "multiempresa",
    }


def test_categoria_conhecimento_inclui_multiempresa():
    assert CategoriaConhecimento.multiempresa.value == "multiempresa"


def test_categorias_do_schema_espelham_os_enums():
    assert schema.INTENCAO == [i.value for i in Intencao]
    assert schema.CATEGORIA_ERP == [c.value for c in CategoriaERP]
    # Base de conhecimento e regras de roteamento compartilham o mesmo vocabulário.
    assert schema.CATEGORIA_CONHECIMENTO == schema.CATEGORIA_ERP


def test_outro_nao_e_categoria_valida():
    assert "outro" not in schema.CATEGORIA_ERP
    assert "outro" not in schema.CATEGORIA_CONHECIMENTO
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_models.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.models.departamento'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/models/departamento.py`:

```python
"""Taxonomia de domínio de departamentos e roteamento.

Este módulo contém **apenas enums** (sem ORM): ele sobrevive à remoção da
camada SQLAlchemy legada planejada na Trilha R2. Os enums são a fonte
canônica; `app/appwrite/schema.py` deriva as listas de valores deles.
"""

import enum


class Intencao(enum.StrEnum):
    """As 9 intenções da taxonomia inicial (docs/specs/05-ai-pipeline.md)."""

    problema_tecnico = "problema_tecnico"
    duvida_uso_erp = "duvida_uso_erp"
    solicitacao_financeira = "solicitacao_financeira"
    solicitacao_comercial = "solicitacao_comercial"
    solicitacao_administrativa = "solicitacao_administrativa"
    implantacao_treinamento = "implantacao_treinamento"
    solicitacao_humano = "solicitacao_humano"
    duvida_geral = "duvida_geral"
    intencao_desconhecida = "intencao_desconhecida"


class CategoriaERP(enum.StrEnum):
    """Módulos do ERP conhecidos pela IA. NÃO é departamento (spec 10).

    `outro` não existe: assunto fora destes módulos é `categoria_erp=null`.
    """

    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"
```

Modify `backend/app/models/knowledge_base.py` — adicionar a linha `multiempresa` após `financeiro`:

```python
class CategoriaConhecimento(enum.StrEnum):
    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"
```

Modify `backend/app/appwrite/schema.py` — substituir a linha 52 e derivar as listas:

```python
from app.models.departamento import CategoriaERP, Intencao
from app.models.knowledge_base import CategoriaConhecimento

INTENCAO = [i.value for i in Intencao]
CATEGORIA_ERP = [c.value for c in CategoriaERP]
CATEGORIA_CONHECIMENTO = [c.value for c in CategoriaConhecimento]
```

(e remover a definição literal antiga `CATEGORIA_CONHECIMENTO = ["fiscal", "estoque", "compras", "vendas", "financeiro"]`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_models.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Expected: mesmo total do baseline + 5, sem erro de lint.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/departamento.py backend/app/models/knowledge_base.py backend/app/appwrite/schema.py backend/tests/test_departamento_models.py
git commit -m "feat(departamentos): enums de intencao e categoria ERP alinhados a taxonomia

- Intencao com as 9 intencoes da spec 05
- CategoriaERP com multiempresa; 'outro' deixa de ser categoria valida
- CATEGORIA_CONHECIMENTO passa a derivar do enum (fim do drift com a IA)
- ATENCAO: mudanca de enum exige atualizacao manual no Appwrite (gap 02-10)"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 02 e 05)**

Em `docs/specs/02-data-model.md`:

```
| 02-1 | `CLASSIFY_SYSTEM` reconhece 7 categorias (`multiempresa`, `outro`); `CATEGORIA_CONHECIMENTO` tem 5 — artigos dessas áreas não podem ser gravados | `ai/prompts.py:5-21` vs `appwrite/schema.py:52` | **Alta** | **CORRIGIDO** — `CATEGORIA_CONHECIMENTO` deriva de `CategoriaConhecimento` (6 categorias, inclui `multiempresa`); `outro` não é categoria válida (`appwrite/schema.py`, `models/departamento.py`) |
| 02-2 | `CategoriaConhecimento` sem `multiempresa`, que é área real do negócio | `appwrite/schema.py:52` | Média | **CORRIGIDO** — `CategoriaConhecimento.multiempresa` (`models/knowledge_base.py`) |
```

Em `docs/specs/05-ai-pipeline.md`:

```
| 05-17 | Categoria `multiempresa` reconhecida pela IA mas ausente do schema | `ai/prompts.py:16` vs `appwrite/schema.py:52` | **Alta** | **CORRIGIDO** — `CATEGORIA_CONHECIMENTO` inclui `multiempresa` e espelha `CategoriaERP` (teste `test_categorias_do_schema_espelham_os_enums`) |
```

Include as linhas na mesma edição e no mesmo commit da task (amend se necessário: `git add ... && git commit --amend --no-edit`).

---

### Task F1.2: Coleções `departamentos` e `regras_roteamento` + `departamento_id`

**Files:**
- Modify: `backend/app/appwrite/schema.py:99-198` (`COLLECTIONS`)
- Modify: `backend/tests/test_appwrite_schema.py:83-94`
- Test: `backend/tests/test_departamento_schema.py`

**Interfaces:**
- Consumes: `INTENCAO`, `CATEGORIA_ERP` (F1.1).
- Produces:
  - `COLLECTIONS["departamentos"]` com atributos `codigo`, `nome`, `descricao`, `ativo`, `ordem`, `recebe_transferencias`, `permite_atribuicao_automatica`
  - `COLLECTIONS["regras_roteamento"]` com `intencao`, `subintencao`, `categoria_erp`, `departamento_id`, `prioridade_regra`, `ativo`
  - `COLLECTIONS["atendentes"]` ganha `departamento_id` (opcional)
  - `COLLECTIONS["chats"]` ganha `departamento_id` (opcional)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_schema.py`:

```python
"""Schema Appwrite das colecoes de departamento e roteamento."""

from app.appwrite import schema


def _keys(collection: str) -> set[str]:
    return {a["key"] for a in schema.COLLECTIONS[collection]["attributes"]}


def test_departamentos_tem_os_atributos_da_spec_02():
    assert _keys("departamentos") == {
        "codigo",
        "nome",
        "descricao",
        "ativo",
        "ordem",
        "recebe_transferencias",
        "permite_atribuicao_automatica",
    }


def test_departamentos_codigo_e_unico_por_tamanho_estavel():
    attrs = {a["key"]: a for a in schema.COLLECTIONS["departamentos"]["attributes"]}
    assert attrs["codigo"]["size"] == 80
    assert attrs["codigo"]["required"] is True


def test_regras_roteamento_tem_os_atributos_da_spec_02():
    assert _keys("regras_roteamento") == {
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_id",
        "prioridade_regra",
        "ativo",
    }


def test_regras_roteamento_nao_aceita_intencao_fora_da_taxonomia():
    attrs = {a["key"]: a for a in schema.COLLECTIONS["regras_roteamento"]["attributes"]}
    # intencao e string(80) validada na aplicacao contra o enum Intencao
    assert attrs["intencao"]["size"] == 80
    assert attrs["departamento_id"]["size"] == 36


def test_atendentes_e_chats_tem_departamento_id_opcional():
    assert "departamento_id" in _keys("atendentes")
    assert "departamento_id" in _keys("chats")
    atendentes = {a["key"]: a for a in schema.COLLECTIONS["atendentes"]["attributes"]}
    chats = {a["key"]: a for a in schema.COLLECTIONS["chats"]["attributes"]}
    assert atendentes["departamento_id"]["required"] is False
    assert chats["departamento_id"]["required"] is False


def test_legado_setor_preservado():
    """C6: setor/setor_alvo nao sao removidos nesta fase."""
    assert "setor" in _keys("atendentes")
    assert "setor_alvo" in _keys("chats")
```

Modify `backend/tests/test_appwrite_schema.py` — o teste de contagem passa a esperar 11 coleções:

```python
def test_schema_cobre_as_onze_collections():
    assert set(COLLECTIONS) == {
        "atendentes",
        "clientes",
        "lojas",
        "chats",
        "mensagens",
        "tags",
        "chat_tags",
        "ia_diagnosticos",
        "knowledge_bases",
        "departamentos",
        "regras_roteamento",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_schema.py tests/test_appwrite_schema.py -v`
Expected: FAIL — `KeyError: 'departamentos'` e `test_schema_cobre_as_onze_collections` não existe ainda

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/appwrite/schema.py`, adicionar `departamento_id` nas coleções existentes e as duas novas no final de `COLLECTIONS` (antes do `}` de fechamento):

```python
    "atendentes": {
        "name": "Atendentes",
        "attributes": [
            str_attr("nome", 255),
            str_attr("email", 255),
            str_attr("hash_senha", 255),
            enum_attr("perfil", PERFIL_ATENDENTE, required=False, default="atendente"),
            str_attr("setor", 50, required=False),
            fk_attr("departamento_id", required=False),
            bool_attr("ativo", default=True),
        ],
    },
```

```python
    "chats": {
        "name": "Chats",
        "attributes": [
            fk_attr("cliente_id"),
            fk_attr("loja_id", required=False),
            fk_attr("atendente_id", required=False),
            fk_attr("departamento_id", required=False),
            enum_attr("status", STATUS_CHAT, required=False, default="NOVO"),
            enum_attr("prioridade", PRIORIDADE_CHAT, required=False, default="media"),
            text_attr("resumo_problema"),
            text_attr("solucao_sugerida_ia"),
            text_attr("causa_provavel"),
            float_attr("nivel_confianca_ia"),
            bool_attr("necessita_humano"),
            str_attr("setor_alvo", 50, required=False),
            str_attr("whatsapp_number", 20, required=False),
            datetime_attr("ultima_mensagem_em"),
        ],
    },
```

```python
    "departamentos": {
        "name": "Departamentos",
        "attributes": [
            str_attr("codigo", 80),
            str_attr("nome", 255),
            str_attr("descricao", 1000, required=False),
            bool_attr("ativo", required=True, default=True),
            int_attr("ordem"),
            bool_attr("recebe_transferencias", required=True, default=True),
            bool_attr("permite_atribuicao_automatica", required=True, default=False),
        ],
    },
    "regras_roteamento": {
        "name": "RegrasRoteamento",
        "attributes": [
            str_attr("intencao", 80),
            str_attr("subintencao", 100, required=False),
            str_attr("categoria_erp", 50, required=False),
            fk_attr("departamento_id"),
            int_attr("prioridade_regra", required=True),
            bool_attr("ativo", required=True, default=True),
        ],
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_schema.py tests/test_appwrite_schema.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Expected: PASS (o `FakeStore` agora aceita as novas coleções via `_defaults_for`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/appwrite/schema.py backend/tests/test_departamento_schema.py backend/tests/test_appwrite_schema.py
git commit -m "feat(departamentos): colecoes departamentos e regras_roteamento no schema

- atributos conforme spec 02 (codigo, flags, prioridade_regra)
- departamento_id opcional em atendentes e chats
- setor/setor_alvo preservados (migracao posterior)"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 10 e 02)**

Em `docs/specs/10-departamentos-e-roteamento.md`, linhas 10-1…10-4 e 02-17/02-18 em `docs/specs/02-data-model.md`:

```
| 10-1 | Coleção `departamentos` inexistente | `appwrite/schema.py` | **Alta** | **CORRIGIDO** — `COLLECTIONS["departamentos"]` (`appwrite/schema.py`) + `DepartamentoRepository` (Task F1.3) |
| 10-2 | Coleção `regras_roteamento` inexistente | `appwrite/schema.py` | **Alta** | **CORRIGIDO** — `COLLECTIONS["regras_roteamento"]` + `RegraRoteamentoRepository` (Task F1.3) |
| 10-3 | `atendentes.departamento_id` ausente; `setor` legado é string livre | `appwrite/schema.py:107` | **Alta** | **CORRIGIDO** — `atendentes.departamento_id` (`appwrite/schema.py`) |
| 10-4 | `chats.departamento_id` ausente; `setor_alvo` legado é string livre | `appwrite/schema.py:144` | **Alta** | **CORRIGIDO** — `chats.departamento_id` (`appwrite/schema.py`) |
```

```
| 02-17 | Coleções `departamentos`, `regras_roteamento`, `integracao_chamados` e `integration_outbox` inexistentes | `appwrite/schema.py` | **Alta** | **ABERTO (parcial)** — `departamentos`/`regras_roteamento` criadas; `integracao_chamados`/`integration_outbox` bloqueadas pelo gap 11-1 |
| 02-18 | `departamento_id` ausente em `atendentes`/`chats` | `appwrite/schema.py` | **Alta** | **CORRIGIDO** — `departamento_id` em `atendentes`/`chats` |
```

---

### Task F1.3: `DepartamentoRepository` e `RegraRoteamentoRepository`

**Files:**
- Create: `backend/app/appwrite/repositories/departamento.py`
- Modify: `backend/app/appwrite/repositories/__init__.py:1-32`
- Modify: `backend/tests/conftest.py:67-110`
- Test: `backend/tests/test_departamento_repository.py`

**Interfaces:**
- Consumes: coleções de F1.2; `BaseRepository` (`get`, `list_all`, `create`, `update`, `delete`, `get_by`, `list_by`).
- Produces:
  - `DepartamentoRepository.get_by_codigo(codigo: str) -> dict | None`
  - `DepartamentoRepository.list_ativos() -> list[dict]`
  - `RegraRoteamentoRepository.list_ativas_ordenadas() -> list[dict]` (ordenado por `prioridade_regra` ASC; menor número = maior prioridade)
  - `Repositories.departamentos`, `Repositories.regras_roteamento`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_repository.py`:

```python
"""Repositorios de departamento e regras de roteamento (fakes em memoria)."""

import pytest


@pytest.mark.asyncio
async def test_get_by_codigo(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro"}
    )
    doc = await fake_repos.departamentos.get_by_codigo("financeiro")
    assert doc is not None
    assert doc["nome"] == "Financeiro"


@pytest.mark.asyncio
async def test_get_by_codigo_inexistente_retorna_none(fake_repos):
    assert await fake_repos.departamentos.get_by_codigo("nao_existe") is None


@pytest.mark.asyncio
async def test_list_ativos_ignora_inativos(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "ativo", "nome": "Ativo", "ativo": True}
    )
    await fake_repos.departamentos.create(
        {"codigo": "inativo", "nome": "Inativo", "ativo": False}
    )
    ativos = await fake_repos.departamentos.list_ativos()
    assert [d["codigo"] for d in ativos] == ["ativo"]


@pytest.mark.asyncio
async def test_list_ativas_ordenadas_por_prioridade(fake_repos):
    await fake_repos.regras_roteamento.create(
        {"intencao": "duvida_geral", "prioridade_regra": 50, "ativo": True}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "prioridade_regra": 10, "ativo": True}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "solicitacao_humano", "prioridade_regra": 1, "ativo": False}
    )
    regras = await fake_repos.regras_roteamento.list_ativas_ordenadas()
    assert [r["intencao"] for r in regras] == ["problema_tecnico", "duvida_geral"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_repository.py -v`
Expected: FAIL com `AttributeError: 'FakeRepositories' object has no attribute 'departamentos'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/appwrite/repositories/departamento.py`:

```python
from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class DepartamentoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "departamentos")

    async def get_by_codigo(self, codigo: str) -> dict | None:
        return await self.get_by("codigo", codigo)

    async def list_ativos(self) -> list[dict]:
        return [d for d in await self.list_all() if d.get("ativo")]


class RegraRoteamentoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "regras_roteamento")

    async def list_ativas_ordenadas(self) -> list[dict]:
        """Menor `prioridade_regra` primeiro (maior prioridade)."""
        regras = [r for r in await self.list_all() if r.get("ativo")]
        return sorted(regras, key=lambda r: r.get("prioridade_regra") or 0)
```

Modify `backend/app/appwrite/repositories/__init__.py`:

```python
from appwrite.services.databases import Databases

from app.appwrite.repositories.atendente import AtendenteRepository
from app.appwrite.repositories.chat import ChatRepository
from app.appwrite.repositories.cliente import ClienteRepository
from app.appwrite.repositories.departamento import (
    DepartamentoRepository,
    RegraRoteamentoRepository,
)
from app.appwrite.repositories.ia_diagnostico import IADiagnosticoRepository
from app.appwrite.repositories.knowledge_base import KnowledgeBaseRepository
from app.appwrite.repositories.loja import LojaRepository
from app.appwrite.repositories.mensagem import MensagemRepository


class Repositories:
    def __init__(self, databases: Databases):
        self.databases = databases
        self.atendentes = AtendenteRepository(databases)
        self.clientes = ClienteRepository(databases)
        self.lojas = LojaRepository(databases)
        self.chats = ChatRepository(databases)
        self.mensagens = MensagemRepository(databases)
        self.ia_diagnosticos = IADiagnosticoRepository(databases)
        self.knowledge_bases = KnowledgeBaseRepository(databases)
        self.departamentos = DepartamentoRepository(databases)
        self.regras_roteamento = RegraRoteamentoRepository(databases)

    def __getattr__(self, name):
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")
```

Modify `backend/tests/conftest.py` — adicionar após `FakeIADiagnosticos`:

```python
class FakeDepartamentos(FakeStore):
    async def get_by_codigo(self, codigo: str) -> dict | None:
        return await self.get_by("codigo", codigo)

    async def list_ativos(self) -> list[dict]:
        return [d for d in await self.list_all() if d.get("ativo")]


class FakeRegrasRoteamento(FakeStore):
    async def list_ativas_ordenadas(self) -> list[dict]:
        regras = [r for r in await self.list_all() if r.get("ativo")]
        return sorted(regras, key=lambda r: r.get("prioridade_regra") or 0)
```

e em `FakeRepositories.__init__`:

```python
        self.departamentos = FakeDepartamentos("departamentos")
        self.regras_roteamento = FakeRegrasRoteamento("regras_roteamento")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_repository.py -v`
Expected: PASS (4 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/appwrite/repositories/departamento.py backend/app/appwrite/repositories/__init__.py backend/tests/conftest.py backend/tests/test_departamento_repository.py
git commit -m "feat(departamentos): repositorios de departamento e regras de roteamento

- get_by_codigo/list_ativos e list_ativas_ordenadas (prioridade ASC)
- registrados no agregado Repositories e nos fakes de teste"
```

---

### Task F1.4: `DepartamentoService` e DTOs

**Files:**
- Create: `backend/app/schemas/departamento.py`
- Create: `backend/app/services/departamento_service.py`
- Test: `backend/tests/test_departamento_service.py`

**Interfaces:**
- Consumes: `Repositories.departamentos`, `.regras_roteamento`, `.chats`, `.atendentes` (F1.3).
- Produces:
  - `DepartamentoService(repos)`
    - `listar(incluir_inativos: bool = False) -> list[dict]`
    - `obter(departamento_id: str) -> dict` (404 se ausente)
    - `criar(data: dict) -> dict` (409 se `codigo` duplicado; normaliza `codigo` para lowercase)
    - `atualizar(departamento_id: str, data: dict) -> dict`
    - `desativar(departamento_id: str) -> dict` (409 se houver vínculos)
    - `listar_atendentes(departamento_id: str) -> list[dict]`
  - DTOs `DepartamentoCreate`, `DepartamentoUpdate`, `DepartamentoResponse`, `RegraRoteamentoResponse`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_service.py`:

```python
"""Regras de negocio de departamento: unicidade, desativacao e ordenacao."""

import pytest
from fastapi import HTTPException

from app.services.departamento_service import DepartamentoService


@pytest.mark.asyncio
async def test_criar_normaliza_codigo_minusculo(fake_repos):
    service = DepartamentoService(fake_repos)
    doc = await service.criar({"codigo": "Suporte_Tecnico", "nome": "Suporte Técnico"})
    assert doc["codigo"] == "suporte_tecnico"
    assert doc["ativo"] is True


@pytest.mark.asyncio
async def test_criar_codigo_duplicado_retorna_409(fake_repos):
    service = DepartamentoService(fake_repos)
    await service.criar({"codigo": "financeiro", "nome": "Financeiro"})
    with pytest.raises(HTTPException) as exc:
        await service.criar({"codigo": "financeiro", "nome": "Outro nome"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_obter_inexistente_retorna_404(fake_repos):
    service = DepartamentoService(fake_repos)
    with pytest.raises(HTTPException) as exc:
        await service.obter("nao-existe")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_listar_ordena_por_ordem_e_nome(fake_repos):
    service = DepartamentoService(fake_repos)
    await service.criar({"codigo": "b", "nome": "Beta", "ordem": 2})
    await service.criar({"codigo": "a", "nome": "Alfa", "ordem": 1})
    await service.criar({"codigo": "c", "nome": "Gama", "ordem": None})
    codigos = [d["codigo"] for d in await service.listar()]
    assert codigos == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_listar_sem_inativos_por_padrao(fake_repos):
    service = DepartamentoService(fake_repos)
    a = await service.criar({"codigo": "a", "nome": "Alfa"})
    await service.atualizar(a["id"], {"ativo": False})
    assert await service.listar() == []
    assert len(await service.listar(incluir_inativos=True)) == 1


@pytest.mark.asyncio
async def test_desativar_bloqueia_quando_ha_regra_vinculada(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "fiscal", "nome": "Fiscal"})
    await fake_repos.regras_roteamento.create(
        {
            "intencao": "problema_tecnico",
            "departamento_id": depto["id"],
            "prioridade_regra": 10,
            "ativo": True,
        }
    )
    with pytest.raises(HTTPException) as exc:
        await service.desativar(depto["id"])
    assert exc.value.status_code == 409
    assert "regras_roteamento" in exc.value.detail


@pytest.mark.asyncio
async def test_desativar_sem_vinculos_marca_inativo(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "comercial", "nome": "Comercial"})
    atualizado = await service.desativar(depto["id"])
    assert atualizado["ativo"] is False


@pytest.mark.asyncio
async def test_listar_atendentes_so_ativos_do_departamento(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "financeiro", "nome": "Financeiro"})
    await fake_repos.atendentes.create(
        {"nome": "A1", "email": "a1@x.com", "departamento_id": depto["id"], "ativo": True}
    )
    await fake_repos.atendentes.create(
        {"nome": "A2", "email": "a2@x.com", "departamento_id": depto["id"], "ativo": False}
    )
    await fake_repos.atendentes.create(
        {"nome": "A3", "email": "a3@x.com", "departamento_id": "outro", "ativo": True}
    )
    atendentes = await service.listar_atendentes(depto["id"])
    assert [a["nome"] for a in atendentes] == ["A1"]


@pytest.mark.asyncio
async def test_codigo_nao_pode_ser_alterado(fake_repos):
    """Codigo e slug estavel: a atualizacao ignora a chave se enviada."""
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "suporte_tecnico", "nome": "Suporte"})
    atualizado = await service.atualizar(
        depto["id"], {"codigo": "renomeado", "nome": "Suporte Técnico"}
    )
    assert atualizado["codigo"] == "suporte_tecnico"
    assert atualizado["nome"] == "Suporte Técnico"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_service.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.services.departamento_service'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/schemas/departamento.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class DepartamentoCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int | None = None
    recebe_transferencias: bool = True
    permite_atribuicao_automatica: bool = False


class DepartamentoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int | None = None
    ativo: bool | None = None
    recebe_transferencias: bool | None = None
    permite_atribuicao_automatica: bool | None = None


class DepartamentoResponse(BaseModel):
    id: str
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool
    ordem: int | None = None
    recebe_transferencias: bool
    permite_atribuicao_automatica: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegraRoteamentoResponse(BaseModel):
    id: str
    intencao: str
    subintencao: str | None = None
    categoria_erp: str | None = None
    departamento_id: str
    prioridade_regra: int
    ativo: bool

    model_config = {"from_attributes": True}
```

Create `backend/app/services/departamento_service.py`:

```python
from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories

_CAMPOS_IMUTAVEIS = {"id", "codigo", "created_at", "updated_at"}


class DepartamentoService:
    """CRUD de departamento e consulta das regras de roteamento.

    `codigo` é slug estável: não muda depois de referenciado por regras
    (docs/specs/02-data-model.md §departamentos).
    """

    def __init__(self, repos: Repositories):
        self.repos = repos

    async def listar(self, incluir_inativos: bool = False) -> list[dict]:
        deptos = await self.repos.departamentos.list_all()
        if not incluir_inativos:
            deptos = [d for d in deptos if d.get("ativo")]
        return sorted(
            deptos,
            key=lambda d: (d.get("ordem") is None, d.get("ordem") or 0, d.get("nome") or ""),
        )

    async def obter(self, departamento_id: str) -> dict:
        depto = await self.repos.departamentos.get(departamento_id)
        if not depto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Departamento não encontrado",
            )
        return depto

    async def criar(self, data: dict) -> dict:
        codigo = str(data["codigo"]).strip().lower()
        if await self.repos.departamentos.get_by_codigo(codigo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Departamento com código '{codigo}' já existe",
            )
        payload = {k: v for k, v in data.items() if k not in _CAMPOS_IMUTAVEIS}
        payload["codigo"] = codigo
        payload.setdefault("ativo", True)
        return await self.repos.departamentos.create(payload)

    async def atualizar(self, departamento_id: str, data: dict) -> dict:
        await self.obter(departamento_id)
        payload = {
            k: v
            for k, v in data.items()
            if k not in _CAMPOS_IMUTAVEIS and v is not None
        }
        if not payload:
            return await self.obter(departamento_id)
        return await self.repos.departamentos.update(departamento_id, payload)

    async def desativar(self, departamento_id: str) -> dict:
        await self.obter(departamento_id)
        vinculos = await self._vinculos(departamento_id)
        if vinculos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Departamento ainda referenciado por: " + ", ".join(vinculos)
                ),
            )
        return await self.repos.departamentos.update(
            departamento_id, {"ativo": False}
        )

    async def _vinculos(self, departamento_id: str) -> list[str]:
        motivos: list[str] = []
        if await self.repos.chats.list_by("departamento_id", departamento_id):
            motivos.append("chats")
        if await self.repos.atendentes.list_by("departamento_id", departamento_id):
            motivos.append("atendentes")
        if await self.repos.regras_roteamento.list_by("departamento_id", departamento_id):
            motivos.append("regras_roteamento")
        return motivos

    async def listar_atendentes(self, departamento_id: str) -> list[dict]:
        await self.obter(departamento_id)
        atendentes = await self.repos.atendentes.list_by(
            "departamento_id", departamento_id
        )
        return [a for a in atendentes if a.get("ativo")]

    async def regras_por_prioridade(self) -> list[dict]:
        return await self.repos.regras_roteamento.list_ativas_ordenadas()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_service.py -v`
Expected: PASS (9 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/departamento.py backend/app/services/departamento_service.py backend/tests/test_departamento_service.py
git commit -m "feat(departamentos): service de departamento com unicidade e bloqueio de desativacao

- codigo normalizado e imutavel apos criacao
- 409 para codigo duplicado e para desativacao com vinculos
- listagem ordenada por ordem/nome"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 02)**

Em `docs/specs/02-data-model.md`:

```
| 02-12 | Sem índice único: unicidade de `email`/`documento` é check-then-insert, vulnerável a corrida | `appwrite/schema.py:14-15` | Média | **CORRIGIDO (departamentos)** — `DepartamentoService.criar` centraliza o check-then-insert de `codigo` com 409; demais entidades seguem pendentes |
```

---

### Task F1.5: Rotas `/departamentos`

**Files:**
- Create: `backend/app/api/routes/departamentos.py`
- Modify: `backend/app/api/routes/__init__.py:1-27`
- Modify: `backend/app/main.py:8-21,59-71`
- Test: `backend/tests/test_departamento_rotas.py`

**Interfaces:**
- Consumes: `DepartamentoService` (F1.4), `get_repositories`, `get_current_user`, `require_perfil` (`api/deps.py`).
- Produces: `departamentos_router` com
  - `GET /departamentos?incluir_inativos=bool` → `list[DepartamentoResponse]`
  - `POST /departamentos` → 201 `DepartamentoResponse`
  - `GET /departamentos/{departamento_id}` → `DepartamentoResponse`
  - `PATCH /departamentos/{departamento_id}` → `DepartamentoResponse`
  - `DELETE /departamentos/{departamento_id}` → 200 `DepartamentoResponse` (desativação)
  - `GET /departamentos/{departamento_id}/atendentes` → `list[dict]` (admin/supervisor)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_rotas.py`:

```python
"""Contrato HTTP dos endpoints de departamento."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_cria_e_lista_departamento(client, admin_token):
    resp = await client.post(
        "/departamentos",
        json={"codigo": "suporte_tecnico", "nome": "Suporte Técnico"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["codigo"] == "suporte_tecnico"
    assert corpo["ativo"] is True

    lista = await client.get("/departamentos", headers=_auth(admin_token))
    assert lista.status_code == 200
    assert [d["codigo"] for d in lista.json()] == ["suporte_tecnico"]


@pytest.mark.asyncio
async def test_atendente_pode_listar_mas_nao_criar(client, atendente_token):
    lista = await client.get("/departamentos", headers=_auth(atendente_token))
    assert lista.status_code == 200

    resp = await client.post(
        "/departamentos",
        json={"codigo": "x", "nome": "X"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_listar_inativos_exige_admin_ou_supervisor(client, atendente_token):
    resp = await client.get(
        "/departamentos?incluir_inativos=true", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_codigo_duplicado_retorna_409(client, admin_token):
    await client.post(
        "/departamentos",
        json={"codigo": "financeiro", "nome": "Financeiro"},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        "/departamentos",
        json={"codigo": "financeiro", "nome": "Financeiro 2"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_detalhe_inexistente_retorna_404(client, admin_token):
    resp = await client.get("/departamentos/nao-existe", headers=_auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_atualiza_nome(client, admin_token):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "comercial", "nome": "Comercial"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    resp = await client.patch(
        f"/departamentos/{depto_id}",
        json={"nome": "Comercial e Novos Negócios"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Comercial e Novos Negócios"


@pytest.mark.asyncio
async def test_delete_desativa(client, admin_token):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "administrativo", "nome": "Administrativo"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    resp = await client.delete(f"/departamentos/{depto_id}", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["ativo"] is False


@pytest.mark.asyncio
async def test_atendentes_do_departamento(client, admin_token, fake_repos):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "implantacao", "nome": "Implantação"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    await fake_repos.atendentes.create(
        {
            "nome": "Implantador",
            "email": "imp@test.com",
            "departamento_id": depto_id,
            "ativo": True,
        }
    )
    resp = await client.get(
        f"/departamentos/{depto_id}/atendentes", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert [a["nome"] for a in resp.json()] == ["Implantador"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_rotas.py -v`
Expected: FAIL com `404 Not Found` em `POST /departamentos` (rota inexistente)

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/api/routes/departamentos.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.schemas.departamento import (
    DepartamentoCreate,
    DepartamentoResponse,
    DepartamentoUpdate,
    RegraRoteamentoResponse,
)
from app.services.departamento_service import DepartamentoService

router = APIRouter(prefix="/departamentos", tags=["Departamentos"])


@router.get("", response_model=list[DepartamentoResponse])
async def listar_departamentos(
    incluir_inativos: bool = Query(False),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    if incluir_inativos and user["perfil"] not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para listar departamentos inativos",
        )
    return await DepartamentoService(repos).listar(incluir_inativos)


@router.post("", response_model=DepartamentoResponse, status_code=201)
async def criar_departamento(
    body: DepartamentoCreate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).criar(body.model_dump())


@router.get("/{departamento_id}", response_model=DepartamentoResponse)
async def obter_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    return await DepartamentoService(repos).obter(departamento_id)


@router.patch("/{departamento_id}", response_model=DepartamentoResponse)
async def atualizar_departamento(
    departamento_id: str,
    body: DepartamentoUpdate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).atualizar(
        departamento_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{departamento_id}", response_model=DepartamentoResponse)
async def desativar_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).desativar(departamento_id)


@router.get("/{departamento_id}/atendentes", response_model=list[dict])
async def listar_atendentes_do_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    return await DepartamentoService(repos).listar_atendentes(departamento_id)


@router.get("/{departamento_id}/regras", response_model=list[RegraRoteamentoResponse])
async def listar_regras_do_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    await DepartamentoService(repos).obter(departamento_id)
    return await repos.regras_roteamento.list_by("departamento_id", departamento_id)
```

Modify `backend/app/api/routes/__init__.py` — adicionar import e `__all__`:

```python
from app.api.routes.departamentos import router as departamentos_router
```

```python
    "departamentos_router",
```

Modify `backend/app/main.py`:

```python
from app.api.routes import (
    atendentes_router,
    auth_router,
    chats_router,
    clientes_router,
    dashboard_router,
    departamentos_router,
    evolution_router,
    kanban_router,
    knowledge_base_router,
    mensagens_router,
    usuarios_router,
    webhooks_router,
    whatsapp_router,
)
```

```python
app.include_router(departamentos_router)
```

(inserir antes de `app.include_router(auth_router)`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_rotas.py -v`
Expected: PASS (8 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/departamentos.py backend/app/api/routes/__init__.py backend/app/main.py backend/tests/test_departamento_rotas.py
git commit -m "feat(departamentos): endpoints de CRUD e atendentes do departamento

- GET/POST /departamentos, GET/PATCH/DELETE /departamentos/{id}
- GET /departamentos/{id}/atendentes (admin/supervisor)
- GET /departamentos/{id}/regras"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 10 e 03)**

Em `docs/specs/10-departamentos-e-roteamento.md`:

```
| 10-5 | Endpoints de CRUD `/departamentos*` inexistentes | `api/routes/` | **Alta** | **CORRIGIDO** — `api/routes/departamentos.py` (6 endpoints) + `DepartamentoService` |
```

Em `docs/specs/03-api-contract.md`:

```
| 03-19 | Endpoints-alvo inexistentes: `/departamentos*`, `/chats/{id}/transferir-departamento`, `/atribuir-atendente`, `/roteamento`, `/ai/classificar-intencao`, `/integracoes/chamados/*` | `api/routes/` | **Alta** | **ABERTO (parcial)** — `/departamentos*` implementados; faltam `/chats/{id}/transferir-departamento`, `/atribuir-atendente`, `/roteamento`, `/ai/classificar-intencao`, `/integracoes/chamados/*` |
```

---

### Task F1.6: Seed idempotente de departamentos

**Files:**
- Create: `backend/app/services/departamento_seed.py`
- Create: `scripts/seed_departamentos.py`
- Test: `backend/tests/test_departamento_seed.py`

**Interfaces:**
- Consumes: `Repositories.departamentos` (F1.3).
- Produces:
  - `DEPARTAMENTOS_SEED: list[dict]` — os 6 departamentos da spec 10 com `codigo`, `nome`, `ordem`, `descricao`
  - `semear(repos) -> dict` — retorna `{"criados": int, "atualizados": int, "ignorados": int}`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departamento_seed.py`:

```python
"""Seed idempotente dos departamentos iniciais (spec 10)."""

import pytest

from app.services.departamento_seed import DEPARTAMENTOS_SEED, semear


@pytest.mark.asyncio
async def test_seed_cria_os_seis_departamentos(fake_repos):
    relatorio = await semear(fake_repos)
    assert relatorio == {"criados": 6, "atualizados": 0, "ignorados": 0}
    codigos = {d["codigo"] for d in await fake_repos.departamentos.list_all()}
    assert codigos == {
        "suporte_tecnico",
        "financeiro",
        "comercial",
        "administrativo",
        "implantacao",
        "atendimento_geral",
    }


@pytest.mark.asyncio
async def test_seed_e_idempotente(fake_repos):
    await semear(fake_repos)
    relatorio = await semear(fake_repos)
    assert relatorio["criados"] == 0
    assert relatorio["ignorados"] == 6
    assert len(await fake_repos.departamentos.list_all()) == 6


@pytest.mark.asyncio
async def test_seed_nao_reativa_departamento_desativado(fake_repos):
    await semear(fake_repos)
    depto = await fake_repos.departamentos.get_by_codigo("comercial")
    await fake_repos.departamentos.update(depto["id"], {"ativo": False})
    await semear(fake_repos)
    assert (await fake_repos.departamentos.get_by_codigo("comercial"))["ativo"] is False


@pytest.mark.asyncio
async def test_seed_atualiza_nome_quando_diferente(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Fin.", "ativo": True, "ordem": 1}
    )
    relatorio = await semear(fake_repos)
    assert relatorio["atualizados"] == 1
    assert (await fake_repos.departamentos.get_by_codigo("financeiro"))["nome"] == "Financeiro"


def test_atendimento_geral_existe_como_fallback():
    codigos = [d["codigo"] for d in DEPARTAMENTOS_SEED]
    assert "atendimento_geral" in codigos
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_departamento_seed.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.services.departamento_seed'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/departamento_seed.py`:

```python
"""Seed idempotente dos departamentos iniciais.

Os seis codigos vem de docs/specs/10-departamentos-e-roteamento.md.
`atendimento_geral` e o destino de fallback do roteamento (spec 05/10).
"""

from app.appwrite.repositories import Repositories

DEPARTAMENTOS_SEED: list[dict] = [
    {
        "codigo": "suporte_tecnico",
        "nome": "Suporte Técnico",
        "descricao": "Erros, falhas e dúvidas técnicas do ERP",
        "ordem": 1,
    },
    {
        "codigo": "financeiro",
        "nome": "Financeiro",
        "descricao": "Cobrança, boleto, negociação e faturamento",
        "ordem": 2,
    },
    {
        "codigo": "comercial",
        "nome": "Comercial",
        "descricao": "Contratação, propostas e novos produtos",
        "ordem": 3,
    },
    {
        "codigo": "administrativo",
        "nome": "Administrativo",
        "descricao": "Cadastro e assuntos administrativos",
        "ordem": 4,
    },
    {
        "codigo": "implantacao",
        "nome": "Implantação",
        "descricao": "Configuração inicial, migração e treinamento",
        "ordem": 5,
    },
    {
        "codigo": "atendimento_geral",
        "nome": "Atendimento Geral",
        "descricao": "Triagem e solicitações ainda sem setor definido",
        "ordem": 6,
    },
]


async def semear(repos: Repositories) -> dict:
    criados = atualizados = ignorados = 0
    for definicao in DEPARTAMENTOS_SEED:
        existente = await repos.departamentos.get_by_codigo(definicao["codigo"])
        if existente is None:
            await repos.departamentos.create(
                {**definicao, "ativo": True, "recebe_transferencias": True,
                 "permite_atribuicao_automatica": False}
            )
            criados += 1
            continue
        diferencas = {
            k: v
            for k, v in definicao.items()
            if k != "codigo" and existente.get(k) != v
        }
        if diferencas:
            await repos.departamentos.update(existente["id"], diferencas)
            atualizados += 1
        else:
            ignorados += 1
    return {"criados": criados, "atualizados": atualizados, "ignorados": ignorados}
```

Create `scripts/seed_departamentos.py`:

```python
#!/usr/bin/env python3
"""Popula os departamentos iniciais no Appwrite (idempotente)."""

import asyncio
import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.appwrite.bootstrap import ensure_appwrite_schema  # noqa: E402
from app.appwrite.repositories import Repositories  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402
from app.services.departamento_seed import semear  # noqa: E402


async def main() -> None:
    databases = build_appwrite_databases(build_appwrite_client())
    await asyncio.to_thread(ensure_appwrite_schema, databases)
    relatorio = await semear(Repositories(databases))
    print(
        f"departamentos: {relatorio['criados']} criados, "
        f"{relatorio['atualizados']} atualizados, "
        f"{relatorio['ignorados']} sem alteração"
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_departamento_seed.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/departamento_seed.py scripts/seed_departamentos.py backend/tests/test_departamento_seed.py
git commit -m "feat(departamentos): seed idempotente dos seis departamentos iniciais

- nao reativa departamento desativado manualmente
- atualiza apenas campos divergentes (nome/descricao/ordem)
- script thin wrapper em scripts/seed_departamentos.py"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 10)**

```
| 10-9 | Seed idempotente de departamentos inexistente | `scripts/` | Média | **CORRIGIDO** — `services/departamento_seed.py` (`semear`) + `scripts/seed_departamentos.py`, idempotente |
```

---

### Task F1.7: Migração de `setor`/`setor_alvo` para `departamento_id`

**Files:**
- Create: `backend/app/services/migracao_setor_service.py`
- Create: `scripts/migrate_setor_departamento.py`
- Test: `backend/tests/test_migracao_setor.py`

**Interfaces:**
- Consumes: `Repositories.departamentos.get_by_codigo`, `.atendentes`, `.chats`; `DEPARTAMENTOS_SEED` (F1.6).
- Produces:
  - `mapa_legado() -> dict[str, str]` — mapeia cada `setor` legado usado hoje no frontend (`atendimento`, `supervisao`, `programadores`) para um `codigo` de departamento
  - `migrar(repos, aplicar: bool = True) -> dict` com chaves `atendentes`, `chats`, `orfaos` (listas de `{"id", "valor"}`), `aplicado` (bool)

**Regra da spec 02, passo 4:** os campos legados **não** são apagados. Passo 6: auditoria de documentos sem correspondência vai no relatório de órfãos.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_migracao_setor.py`:

```python
"""Migracao de setor/setor_alvo legado para departamento_id (spec 02)."""

import pytest

from app.services.departamento_seed import semear
from app.services.migracao_setor_service import mapa_legado, migrar


@pytest.mark.asyncio
async def test_migra_atendentes_e_chats_preservando_legado(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": "NOVO", "setor_alvo": "supervisao"}
    )

    relatorio = await migrar(fake_repos)

    atendente_db = await fake_repos.atendentes.get(atendente["id"])
    chat_db = await fake_repos.chats.get(chat["id"])
    assert atendente_db["departamento_id"] is not None
    assert chat_db["departamento_id"] is not None
    # C6: legado preservado
    assert atendente_db["setor"] == "atendimento"
    assert chat_db["setor_alvo"] == "supervisao"
    assert relatorio["orfaos"] == []
    assert relatorio["aplicado"] is True


@pytest.mark.asyncio
async def test_setor_desconhecido_vira_orfao_e_nao_recebe_departamento(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "setor_inexistente", "ativo": True}
    )

    relatorio = await migrar(fake_repos)

    assert (await fake_repos.atendentes.get(atendente["id"]))["departamento_id"] is None
    assert relatorio["orfaos"] == [
        {"id": atendente["id"], "origem": "atendentes", "valor": "setor_inexistente"}
    ]


@pytest.mark.asyncio
async def test_dry_run_nao_escreve(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )

    relatorio = await migrar(fake_repos, aplicar=False)

    assert (await fake_repos.atendentes.get(atendente["id"]))["departamento_id"] is None
    assert relatorio["aplicado"] is False
    assert len(relatorio["atendentes"]) == 1


@pytest.mark.asyncio
async def test_migracao_e_idempotente(fake_repos):
    await semear(fake_repos)
    await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )
    await migrar(fake_repos)
    segundo = await migrar(fake_repos)
    assert segundo["atendentes"] == []
    assert segundo["chats"] == []


def test_mapa_legado_cobre_os_setores_do_frontend():
    assert mapa_legado() == {
        "atendimento": "suporte_tecnico",
        "supervisao": "atendimento_geral",
        "programadores": "suporte_tecnico",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_migracao_setor.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.services.migracao_setor_service'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/migracao_setor_service.py`:

```python
"""Migracao dos campos legados `setor`/`setor_alvo` para `departamento_id`.

Passos 2..6 de docs/specs/02-data-model.md §Migracao de setor legado.
O passo 7 (remover o legado) e migracao posterior, fora desta fase.
"""

from app.appwrite.repositories import Repositories

_LEGADO_PARA_CODIGO = {
    "atendimento": "suporte_tecnico",
    "supervisao": "atendimento_geral",
    "programadores": "suporte_tecnico",
}


def mapa_legado() -> dict[str, str]:
    return dict(_LEGADO_PARA_CODIGO)


async def _resolver(repos: Repositories, codigo: str) -> str | None:
    depto = await repos.departamentos.get_by_codigo(codigo)
    return depto["id"] if depto else None


async def migrar(repos: Repositories, aplicar: bool = True) -> dict:
    relatorio: dict = {
        "atendentes": [],
        "chats": [],
        "orfaos": [],
        "aplicado": aplicar,
    }

    for atendente in await repos.atendentes.list_all():
        if atendente.get("departamento_id"):
            continue
        setor = atendente.get("setor")
        if not setor:
            continue
        codigo = _LEGADO_PARA_CODIGO.get(setor)
        departamento_id = await _resolver(repos, codigo) if codigo else None
        if departamento_id is None:
            relatorio["orfaos"].append(
                {"id": atendente["id"], "origem": "atendentes", "valor": setor}
            )
            continue
        relatorio["atendentes"].append(
            {"id": atendente["id"], "setor": setor, "departamento_id": departamento_id}
        )
        if aplicar:
            await repos.atendentes.update(
                atendente["id"], {"departamento_id": departamento_id}
            )

    for chat in await repos.chats.list_all():
        if chat.get("departamento_id"):
            continue
        setor = chat.get("setor_alvo")
        if not setor:
            continue
        codigo = _LEGADO_PARA_CODIGO.get(setor)
        departamento_id = await _resolver(repos, codigo) if codigo else None
        if departamento_id is None:
            relatorio["orfaos"].append(
                {"id": chat["id"], "origem": "chats", "valor": setor}
            )
            continue
        relatorio["chats"].append(
            {"id": chat["id"], "setor_alvo": setor, "departamento_id": departamento_id}
        )
        if aplicar:
            await repos.chats.update(chat["id"], {"departamento_id": departamento_id})

    return relatorio
```

Create `scripts/migrate_setor_departamento.py`:

```python
#!/usr/bin/env python3
"""Migra setor/setor_alvo legado para departamento_id.

Uso:
  python scripts/migrate_setor_departamento.py --dry-run
  python scripts/migrate_setor_departamento.py --apply
"""

import argparse
import asyncio
import json
import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.appwrite.repositories import Repositories  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402
from app.services.migracao_setor_service import migrar  # noqa: E402


async def main(aplicar: bool) -> None:
    repositories = Repositories(build_appwrite_databases(build_appwrite_client()))
    relatorio = await migrar(repositories, aplicar=aplicar)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    if relatorio["orfaos"]:
        print(
            f"\nATENCAO: {len(relatorio['orfaos'])} documento(s) sem correspondencia "
            "de departamento. Corrija manualmente antes do passo 7."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--dry-run", action="store_true")
    grupo.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(aplicar=args.apply))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_migracao_setor.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/migracao_setor_service.py scripts/migrate_setor_departamento.py backend/tests/test_migracao_setor.py
git commit -m "feat(departamentos): migra setor/setor_alvo legado para departamento_id

- preserva os campos legados (spec 02, passo 4)
- relatorio de orfaos para auditoria manual (passo 6)
- idempotente e com modo --dry-run"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 10 e 02)**

```
| 10-10 | Migração de `setor`/`setor_alvo` para `departamento_id` inexistente | `scripts/`; `appwrite/` | **Alta** | **CORRIGIDO** — `services/migracao_setor_service.py` (`migrar`) + `scripts/migrate_setor_departamento.py` |
```

```
| 02-4 | `atendentes.setor` e `chats.setor_alvo` são string livre, sem enum/validação (legado a migrar para departamento) | `appwrite/schema.py:107,144` | Média | **CORRIGIDO (departamento_id)** — legado migrado e preservado; leitura canônica por ID nas Tasks F1.8/F1.9 |
```

---

### Task F1.8: `ChatService` grava `departamento_id`

**Files:**
- Modify: `backend/app/services/chat_service.py:37-92,102-115,142-184`
- Modify: `backend/app/schemas/chat.py:24-68`
- Test: `backend/tests/test_chat_service_departamento.py`

**Interfaces:**
- Consumes: `Repositories.chats`, `.departamentos` (F1.3).
- Produces:
  - `ChatService.criar(data)` aceita e persiste `departamento_id` (valida existência/atividade se informado)
  - `ChatService.assinar`, `.pegar`, `.transferir`, `.transferir_grupo` **preservam** `departamento_id`
  - `ChatService.listar(...)` devolve `departamento_id` em cada item
  - `ChatListResponse.departamento_id: str | None`, `ChatDetailResponse.departamento_id: str | None`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chat_service_departamento.py`:

```python
"""ChatService passa a persistir departamento_id sem quebrar o legado."""

import pytest
from fastapi import HTTPException

from app.services.chat_service import ChatService


async def _depto(fake_repos, codigo="suporte_tecnico"):
    return await fake_repos.departamentos.create(
        {"codigo": codigo, "nome": codigo, "ativo": True}
    )


@pytest.mark.asyncio
async def test_criar_persiste_departamento_id(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await ChatService(fake_repos).criar(
        {"cliente_id": cliente["id"], "departamento_id": depto["id"]}
    )
    assert chat["departamento_id"] == depto["id"]


@pytest.mark.asyncio
async def test_criar_com_departamento_inexistente_retorna_404(fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).criar(
            {"cliente_id": cliente["id"], "departamento_id": "nao-existe"}
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_criar_com_departamento_inativo_retorna_400(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.departamentos.update(depto["id"], {"ativo": False})
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).criar(
            {"cliente_id": cliente["id"], "departamento_id": depto["id"]}
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_pegar_preserva_departamento_e_limpa_setor_legado(fake_repos):
    depto = await _depto(fake_repos)
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": "NOVO",
            "departamento_id": depto["id"],
            "setor_alvo": "atendimento",
        }
    )
    atualizado = await ChatService(fake_repos).pegar(chat["id"], "atendente-1")
    assert atualizado["departamento_id"] == depto["id"]
    assert atualizado["setor_alvo"] is None


@pytest.mark.asyncio
async def test_transferir_preserva_departamento(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.atendentes.create(
        {"nome": "Destino", "email": "d@x.com", "ativo": True}
    )
    destino = (await fake_repos.atendentes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": "EM_ATENDIMENTO", "departamento_id": depto["id"]}
    )
    atualizado = await ChatService(fake_repos).transferir(
        chat["id"], destino["id"], {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["departamento_id"] == depto["id"]
    assert atualizado["atendente_id"] == destino["id"]


@pytest.mark.asyncio
async def test_listar_devolve_departamento_id(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "departamento_id": depto["id"]}
    )
    chats, total = await ChatService(fake_repos).listar()
    assert total == 1
    assert chats[0]["departamento_id"] == depto["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_chat_service_departamento.py -v`
Expected: FAIL — `KeyError: 'departamento_id'` nos chats criados e `departamento_id` ausente na resposta de `listar`

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/chat_service.py`, alterar `criar`:

```python
    async def criar(self, data: dict) -> dict:
        if not await self.repos.clientes.get(data["cliente_id"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
            )
        departamento_id = data.get("departamento_id")
        if departamento_id:
            depto = await self.repos.departamentos.get(departamento_id)
            if not depto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Departamento não encontrado",
                )
            if not depto.get("ativo"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Departamento inativo não aceita novos chats",
                )
        return await self.repos.chats.create(
            {
                "cliente_id": data["cliente_id"],
                "loja_id": data.get("loja_id"),
                "whatsapp_number": data.get("whatsapp_number"),
                "departamento_id": departamento_id,
                "status": StatusChat.novo.value,
                "prioridade": PrioridadeChat.media.value,
            }
        )
```

Em `pegar`, `transferir` e `transferir_grupo`, manter `departamento_id` (não escrever `None`) e limpar apenas o legado:

```python
    async def pegar(self, chat_id: str, atendente_id: str) -> dict:
        chat = await self.obter(chat_id)
        if chat["atendente_id"] is not None and chat["atendente_id"] != atendente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este chamado já está com outro atendente",
            )
        data = {"atendente_id": atendente_id, "setor_alvo": None}
        if chat["status"] == StatusChat.novo:
            data["status"] = StatusChat.em_atendimento.value
        return await self.repos.chats.update(chat_id, data)
```

```python
    async def transferir(self, chat_id: str, novo_atendente_id: str, user: dict) -> dict:
        chat = await self.obter(chat_id)
        if user["perfil"] == "atendente" and chat["atendente_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        if not await self.repos.atendentes.get(novo_atendente_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado"
            )
        data = {"atendente_id": novo_atendente_id, "setor_alvo": None}
        if chat["status"] in (
            StatusChat.aguardando_humano_com_solucao.value,
            StatusChat.aguardando_humano_sem_solucao.value,
            StatusChat.novo.value,
        ):
            data["status"] = StatusChat.em_atendimento.value
        return await self.repos.chats.update(chat_id, data)
```

> Isto também corrige a comparação string × `StrEnum` do gap 01-6/01-7 nesta função: os literais passam a usar `StatusChat.*.value`.

Em `transferir_grupo`, trocar o destino por departamento resolvido a partir do código (o alias por ID chega na Task F2.9):

```python
    async def transferir_grupo(self, chat_id: str, setor: str, user: dict) -> dict:
        chat = await self.obter(chat_id)
        if user["perfil"] == "atendente" and chat["atendente_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        depto = await self.repos.departamentos.get_by_codigo(setor)
        if not depto or not depto.get("ativo"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Departamento '{setor}' inválido ou inativo",
            )
        data = {
            "atendente_id": None,
            "departamento_id": depto["id"],
            "setor_alvo": setor,
        }
        if chat["status"] == StatusChat.em_atendimento.value:
            data["status"] = StatusChat.novo.value
        return await self.repos.chats.update(chat_id, data)
```

Em `listar`, adicionar `"departamento_id": c["departamento_id"]` ao dict de resposta (após `"atendente_id"`).

Em `backend/app/schemas/chat.py`, adicionar o campo em `ChatListResponse` e `ChatDetailResponse`:

```python
    atendente_id: str | None = None
    departamento_id: str | None = None
    setor_alvo: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_chat_service_departamento.py -v`
Expected: PASS (6 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Expected: PASS — `tests/test_chat_service.py` continua verde (comportamento legado preservado).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/schemas/chat.py backend/tests/test_chat_service_departamento.py
git commit -m "feat(chats): ChatService persiste departamento_id e preserva o legado

- criar valida existencia/atividade do departamento
- pegar/transferir nao apagam mais o departamento
- transferir_grupo resolve codigo de departamento validado
- comparacoes de status passam a usar StatusChat.*.value (01-6/01-7)"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 10, 02, 01)**

```
| 10-3 | `atendentes.departamento_id` ausente; `setor` legado é string livre | `appwrite/schema.py:107` | **Alta** | **CORRIGIDO** — `departamento_id` no schema e gravado por `ChatService.criar` |
| 10-4 | `chats.departamento_id` ausente; `setor_alvo` legado é string livre | `appwrite/schema.py:144` | **Alta** | **CORRIGIDO** — `departamento_id` no schema e gravado por `ChatService.criar`/`transferir_grupo` |
```

```
| 02-4 | `atendentes.setor` e `chats.setor_alvo` são string livre, sem enum/validação (legado a migrar para departamento) | `appwrite/schema.py:107,144` | Média | **CORRIGIDO (departamento_id)** — leitura/escrita canônica por ID em `ChatService`; legado preservado |
```

```
| 01-6 | `transferir` usa literais de string; `transferir_grupo` usa o enum | `services/chat_service.py:166-171` | Baixa | **CORRIGIDO** — `transferir` usa `StatusChat.*.value`; `transferir_grupo` resolve departamento por código |
| 01-7 | `chat["status"] == StatusChat.em_atendimento` compara string com membro de `StrEnum` | `services/chat_service.py:182` | Baixa | **CORRIGIDO** — comparações via `StatusChat.em_atendimento.value` |
```

---

### Task F1.9: Visibilidade por departamento em `listar` e no dashboard

**Files:**
- Modify: `backend/app/services/chat_service.py:37-92` (filtro `pode_ver` + filtro por `departamento_id`)
- Modify: `backend/app/services/dashboard_service.py:44-80`
- Modify: `backend/app/api/routes/dashboard.py:11-17`
- Modify: `backend/app/api/routes/chats.py:21-34` (repassa `departamento_id` e `user` por keyword)
- Test: `backend/tests/test_visibilidade_departamento.py`

**Interfaces:**
- Consumes: `departamento_id` em chats/atendentes (F1.8).
- Produces:
  - `ChatService.listar(..., departamento_id: str | None = None, user: dict | None = None)` — atendente vê chats do próprio departamento (ou que já são dele); admin/supervisor veem tudo; `departamento_id` filtra a página **depois** do escopo
  - `GET /chats?departamento_id=` (filtro explícito do operador, aplicado sobre o escopo)
  - `DashboardService.obter_dashboard(user: dict | None = None) -> dict` — aplica o mesmo escopo; `clientes.get` deixa de ser chamado dentro do loop; shape preservado (`kpis`, `por_status`, `recentes`)

**Regra:** `user["departamento_id"]` é a chave do escopo. Atendente **sem** departamento vê apenas os chats que já são dele (fail-closed), nunca a fila global.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_visibilidade_departamento.py`:

```python
"""Escopo por departamento em listagem de chats e dashboard."""

import pytest

from app.services.chat_service import ChatService
from app.services.dashboard_service import DashboardService


async def _cenario(fake_repos):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    await fake_repos.clientes.create({"nome": "C1", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat_suporte = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
         "departamento_id": suporte["id"]}
    )
    chat_financeiro = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO",
         "departamento_id": financeiro["id"]}
    )
    return suporte, financeiro, chat_suporte, chat_financeiro


@pytest.mark.asyncio
async def test_atendente_ve_apenas_seu_departamento(fake_repos):
    suporte, _, chat_suporte, chat_financeiro = await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    chats, total = await ChatService(fake_repos).listar(user=user)
    assert total == 1
    assert chats[0]["id"] == chat_suporte["id"]


@pytest.mark.asyncio
async def test_atendente_sem_departamento_nao_ve_fila_global(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": None}
    chats, total = await ChatService(fake_repos).listar(user=user)
    assert total == 0
    assert chats == []


@pytest.mark.asyncio
async def test_admin_ve_todos(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "admin", "perfil": "admin", "departamento_id": None}
    _, total = await ChatService(fake_repos).listar(user=user)
    assert total == 2


@pytest.mark.asyncio
async def test_atendente_continua_vendo_chat_que_e_dele(fake_repos):
    suporte, financeiro, _, chat_financeiro = await _cenario(fake_repos)
    await fake_repos.chats.update(chat_financeiro["id"], {"atendente_id": "a1"})
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    chats, total = await ChatService(fake_repos).listar(user=user)
    assert total == 1
    assert chats[0]["id"] == chat_financeiro["id"]


@pytest.mark.asyncio
async def test_dashboard_aplica_escopo_do_atendente(fake_repos):
    suporte, _, chat_suporte, _ = await _cenario(fake_repos)
    await fake_repos.mensagens.create(
        {"chat_id": chat_suporte["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    dados = await DashboardService(fake_repos).obter_dashboard(user=user)
    assert dados["kpis"]["total"] == 1
    assert [c["id"] for c in dados["recentes"]] == [chat_suporte["id"]]


@pytest.mark.asyncio
async def test_dashboard_nao_chama_clientes_get_no_loop(fake_repos, monkeypatch):
    suporte, _, chat_suporte, _ = await _cenario(fake_repos)
    chamadas = {"n": 0}
    original = fake_repos.clientes.get

    async def contando(cliente_id):
        chamadas["n"] += 1
        return await original(cliente_id)

    monkeypatch.setattr(fake_repos.clientes, "get", contando)
    user = {"id": "admin", "perfil": "admin", "departamento_id": None}
    await DashboardService(fake_repos).obter_dashboard(user=user)
    assert chamadas["n"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_visibilidade_departamento.py -v`
Expected: FAIL — `test_atendente_ve_apenas_seu_departamento` vê 2 chats; `DashboardService.obter_dashboard` não aceita `user`

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/chat_service.py`, substituir o filtro:

```python
        if user and user["perfil"] == "atendente":
            departamento_id = user.get("departamento_id")

            def pode_ver(c: dict) -> bool:
                if c["atendente_id"] == user["id"]:
                    return True
                if c["atendente_id"] is not None:
                    return False
                if departamento_id:
                    return c.get("departamento_id") == departamento_id
                # Sem departamento: fail-closed no legado (nada de fila global).
                return (
                    c.get("departamento_id") is None
                    and c.get("setor_alvo") is not None
                    and c.get("setor_alvo") == user.get("setor")
                )

            chats = [c for c in chats if pode_ver(c)]
```

Ainda em `backend/app/services/chat_service.py`, o filtro explícito do operador entra **depois** do escopo (nunca antes — senão a query poderia ampliar visão). Assinatura completa:

```python
    async def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        status: StatusChat | None = None,
        cliente_id: str | None = None,
        prioridade: PrioridadeChat | None = None,
        departamento_id: str | None = None,
        user: dict | None = None,
    ) -> tuple[list[dict], int]:
```

e, logo após o bloco `if user and user["perfil"] == "atendente": ...`:

```python
        if departamento_id:
            chats = [c for c in chats if c.get("departamento_id") == departamento_id]
```

Em `backend/app/api/routes/chats.py`, a rota ganha o parâmetro e passa tudo por keyword (a posição de `user` mudou):

```python
@router.get("", response_model=list[ChatListResponse])
async def listar_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: StatusChat | None = Query(None),
    cliente_id: str | None = Query(None),
    prioridade: PrioridadeChat | None = Query(None),
    departamento_id: str | None = Query(None),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    chats, _ = await service.listar(
        skip=skip,
        limit=limit,
        status=status,
        cliente_id=cliente_id,
        prioridade=prioridade,
        departamento_id=departamento_id,
        user=user,
    )
    return chats
```

Acrescente ao mesmo `backend/tests/test_visibilidade_departamento.py` o teste HTTP do filtro (ele também falha antes da mudança de rota, porque o parâmetro é ignorado):

```python
@pytest.mark.asyncio
async def test_rota_de_chats_filtra_por_departamento(
    client, atendente_token, fake_repos
):
    suporte, financeiro, chat_suporte, chat_financeiro = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )

    resp = await client.get(
        "/chats", params={"departamento_id": suporte["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [chat_suporte["id"]]


@pytest.mark.asyncio
async def test_rota_de_chats_nao_amplia_escopo_com_filtro(
    client, atendente_token, fake_repos
):
    suporte, financeiro, _, chat_financeiro = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )

    resp = await client.get(
        "/chats", params={"departamento_id": financeiro["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert resp.status_code == 200
    assert resp.json() == []
```

Em `backend/app/services/dashboard_service.py`, alterar a assinatura e o começo do método (linhas 27-42), o bloco de mensagens (45-59) e o bloco de recentes (72-81):

```python
    async def obter_dashboard(self, user: dict | None = None) -> dict:
        todos = await self.repos.chats.list_all()

        if user and user["perfil"] == "atendente":
            departamento_id = user.get("departamento_id")

            def no_escopo(c: dict) -> bool:
                if c.get("atendente_id") == user["id"]:
                    return True
                if c.get("atendente_id") is not None:
                    return False
                if departamento_id:
                    return c.get("departamento_id") == departamento_id
                return (
                    c.get("departamento_id") is None
                    and c.get("setor_alvo") is not None
                    and c.get("setor_alvo") == user.get("setor")
                )

            todos = [c for c in todos if no_escopo(c)]

        total = len(todos)
```

```python
        mensagens = await self.repos.mensagens.list_all()
        chats_no_escopo = {c["id"] for c in todos}
        atendente_msgs = [
            m
            for m in mensagens
            if m["remetente"] == RemetenteMensagem.atendente.value
            and m["chat_id"] in chats_no_escopo
        ]
```

```python
        recentes = []
        clientes_por_id = {c["id"]: c for c in await self.repos.clientes.list_all()}
        for c in sorted(todos, key=lambda c: c["created_at"] or "", reverse=True)[:10]:
            cliente = clientes_por_id.get(c["cliente_id"])
            recentes.append({
                "id": c["id"],
                "cliente_nome": cliente["nome"] if cliente else None,
                "status": c["status"],
                "prioridade": c["prioridade"],
                "created_at": c["created_at"],
            })
```

O resto do método (`por_status`, o retorno com `kpis`/`por_status`/`recentes`) permanece idêntico.

Em `backend/app/api/routes/dashboard.py`:

```python
@router.get("", response_model=DashboardResponse)
async def obter_dashboard(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = DashboardService(repos)
    return await service.obter_dashboard(user=user)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_visibilidade_departamento.py -v`
Expected: PASS (6 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/services/dashboard_service.py backend/app/api/routes/dashboard.py backend/tests/test_visibilidade_departamento.py
git commit -m "feat(rbac): escopo por departamento em chats e dashboard

- atendente ve apenas o proprio departamento ou chats que ja sao seus
- atendente sem departamento nao ve fila global (fail-closed)
- dashboard deixa de chamar clientes.get dentro do loop (02-15)"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 04, 03, 02, 01, 10)**

```
| 04-1 | `GET /dashboard` não aplica filtro de visibilidade; atendente lê KPIs globais e nomes de clientes | `api/routes/dashboard.py`; `services/dashboard_service.py` | **Alta** | **CORRIGIDO** — `DashboardService.obter_dashboard(user=...)` aplica escopo por departamento |
| 04-10 | Escopo por departamento não é aplicado (departamento não existe) | `services/chat_service.py` | **Alta** | **CORRIGIDO** — `ChatService.listar` filtra por `departamento_id` |
```

```
| 03-1 | `GET /dashboard` não aplica filtro de visibilidade | `api/routes/dashboard.py:11-17` | **Alta** | **CORRIGIDO** — `routes/dashboard.py` passa `user` (mesma correção de 04-1) |
```

```
| 02-15 | `dashboard_service.py` chama `clientes.get` dentro do loop de recentes | `services/dashboard_service.py:73-74` | Média | **CORRIGIDO** — `clientes.list_all()` fora do loop em `DashboardService` |
```

```
| 01-9 | Sem entidade departamento nem atribuição por departamento na máquina de estados | `appwrite/schema.py`; `services/chat_service.py` | **Alta** | **CORRIGIDO** — departamento participa da visibilidade e da atribuição em `ChatService` |
```

---

### Task F1.10: Guarda de posse nos endpoints de detalhe

**Files:**
- Modify: `backend/app/services/chat_service.py` (novo `obter_com_escopo`)
- Modify: `backend/app/api/routes/chats.py:36-43`
- Modify: `backend/app/api/routes/mensagens.py` (rota `listar_mensagens`)
- Modify: `backend/app/api/routes/clientes.py:obter_cliente`
- Test: `backend/tests/test_posse_chat.py`

**Interfaces:**
- Consumes: `ChatService.listar`/`pode_ver` (F1.9).
- Produces:
  - `ChatService.obter_com_escopo(chat_id: str, user: dict) -> dict` — 404 se não existe, **403** se fora do escopo do atendente
  - `ChatService.pode_ver_chat(chat: dict, user: dict) -> bool` — regra única reutilizada por mensagens e clientes

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_posse_chat.py`:

```python
"""Posse/escopo em GET /chats/{id}, /chats/{id}/mensagens e /clientes/{id}."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_atendente_nao_le_chat_de_outro_departamento(
    client, atendente_token, fake_repos
):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
            "departamento_id": financeiro["id"],
        }
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_le_chat_do_proprio_departamento(
    client, atendente_token, fake_repos
):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "NOVO",
            "departamento_id": suporte["id"],
        }
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_le_qualquer_chat(client, admin_token, fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_atendente_nao_lista_mensagens_fora_do_escopo(
    client, atendente_token, fake_repos
):
    await fake_repos.departamentos.create(
        {"codigo": "comercial", "nome": "Comercial", "ativo": True}
    )
    comercial = await fake_repos.departamentos.get_by_codigo("comercial")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "departamento_id": comercial["id"]}
    )
    resp = await client.get(
        f"/chats/{chat['id']}/mensagens", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_posse_chat.py -v`
Expected: FAIL — todos devolvem 200 (nenhuma checagem de posse)

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/chat_service.py`, extrair a regra e usá-la nos dois pontos:

```python
    def pode_ver_chat(self, chat: dict, user: dict) -> bool:
        if user["perfil"] in ("admin", "supervisor"):
            return True
        if chat.get("atendente_id") == user["id"]:
            return True
        if chat.get("atendente_id") is not None:
            return False
        departamento_id = user.get("departamento_id")
        if departamento_id:
            return chat.get("departamento_id") == departamento_id
        return (
            chat.get("departamento_id") is None
            and chat.get("setor_alvo") is not None
            and chat.get("setor_alvo") == user.get("setor")
        )

    async def obter_com_escopo(self, chat_id: str, user: dict) -> dict:
        chat = await self.obter(chat_id)
        if not self.pode_ver_chat(chat, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat fora do seu escopo de acesso",
            )
        return chat
```

Refatorar `listar` para usar `self.pode_ver_chat` no lugar do `pode_ver` local (mesma regra, uma fonte):

```python
        if user and user["perfil"] != "admin" and user["perfil"] != "supervisor":
            chats = [c for c in chats if self.pode_ver_chat(c, user)]
```

Em `backend/app/api/routes/chats.py`:

```python
@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def obter_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.obter_com_escopo(chat_id, user)
```

Em `backend/app/api/routes/mensagens.py`, na rota `GET /chats/{chat_id}/mensagens`, antes de listar:

```python
    await ChatService(repos).obter_com_escopo(chat_id, user)
```

Em `backend/app/api/routes/clientes.py`, na rota `GET /clientes/{cliente_id}`, permitir somente quando o solicitante é admin/supervisor **ou** tem escopo sobre algum chat do cliente:

```python
    service = ChatService(repos)
    if user["perfil"] not in ("admin", "supervisor"):
        chats_do_cliente = await repos.chats.list_by("cliente_id", cliente_id)
        if not any(service.pode_ver_chat(c, user) for c in chats_do_cliente):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cliente fora do seu escopo de acesso",
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_posse_chat.py -v`
Expected: PASS (4 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/api/routes/chats.py backend/app/api/routes/mensagens.py backend/app/api/routes/clientes.py backend/tests/test_posse_chat.py
git commit -m "fix(rbac): aplica posse/escopo em detalhe de chat, mensagens e cliente

- ChatService.pode_ver_chat como regra unica (reusada por listar)
- obter_com_escopo devolve 403 fora do departamento
- /clientes/{id} exige escopo sobre algum chat do cliente"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 04 e 03)**

```
| 04-2 | `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse | `api/routes/chats.py`; `mensagens.py`; `clientes.py` | **Alta** | **CORRIGIDO** — `ChatService.pode_ver_chat` + `obter_com_escopo` em `/chats/{id}`, `/chats/{id}/mensagens`, `/clientes/{id}` |
| 03-2 | `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse | `api/routes/chats.py:36-43`; `mensagens.py`; `clientes.py` | **Alta** | **CORRIGIDO** — mesma correção de 04-2 |
```

---

## Gate G1 — critério de saída da Fase 1

Antes de iniciar a Fase 2, confirmar:

- [ ] `pytest tests/ -q` verde, com os 10 arquivos de teste novos da fase passando.
- [ ] `ruff check app tests` sem erro.
- [ ] `COLLECTIONS` contém `departamentos` e `regras_roteamento`; `atendentes`/`chats` contêm `departamento_id`.
- [ ] `scripts/seed_departamentos.py` roda em dry-run conceitual: `semear` é idempotente (testado).
- [ ] `migrar(repos, aplicar=False)` devolve relatório de órfãos e não escreve (testado).
- [ ] Registros de Gaps das specs 02, 03, 04, 05, 10 e 01 atualizados nas linhas listadas no Rastreio.
- [ ] Passo manual registrado no PR/commit: atualizar o enum `categoria` de `knowledge_bases` no Appwrite (gap 02-10).

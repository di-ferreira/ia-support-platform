# Fase 3 — Diagnóstico, Snapshot de Roteamento e Ciclo de Resolução

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O pipeline de IA passa a classificar a intenção, resolver o departamento por regra, consultar a base apenas quando faz sentido, persistir o snapshot completo do diagnóstico (intenção, categoria ERP, destino sugerido/final, motivo, artigos consultados) e fechar o ciclo dos três cenários — incluindo confirmação de resolução e reabertura.

**Architecture:** `AIPipelineService` continua sendo o único dono do fluxo. Ele orquestra `IntentClassifier` (F2.2) e `RoutingService` (F2.4), mas **não decide nada por conta própria**: o LLM produz a classificação, o resolver devolve o destino, o pipeline apenas aplica e persiste. Toda mudança de status continua passando por `ChatService.atualizar_status` (C7) e o `departamento_id` é aplicado com `repos.chats.update` (nunca direto no status).

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest + pytest-asyncio; LLM e embedder injetados por monkeypatch nos testes (`FakeLLM`/`FakeEmbedder`), Qdrant substituído por fake — nenhuma rede (C12).

**Specs:** `docs/specs/05-ai-pipeline.md` (§Etapas do pipeline, §Pipeline RAG técnico, §Três cenários de decisão, §Persistência e eventos), `docs/specs/10-departamentos-e-roteamento.md`, `docs/specs/02-data-model.md` (§`ia_diagnosticos`), `docs/specs/01-domain-glossary.md` (§ciclo de vida).

## Global Constraints

Vale `README.md` §Global Constraints (C1–C12). Em especial: **C7** (status só via `ChatService.atualizar_status`), **C8** (LLM sugere, roteamento decide) e **C12** (fakes, sem banco real).

**Gate de entrada:** G2 (Fases 1 e 2 concluídas — `departamento_id`, `regras_roteamento`, `RoutingService` e `PostClassification`/`ClassificacaoIntencao` existem).

## Rastreio gap → task

| Gap | Task | Evidência que fecha |
|---|---|---|
| 02-19 | F3.1 | `ia_diagnosticos` ganha `intencao`, `subintencao`, `categoria_erp`, `departamento_sugerido_codigo`, `departamento_id`, `motivo`, `artigos_consultados` |
| 05-23 | F3.1, F3.3, F3.4 | snapshot completo gravado por `_finalizar` (intenção, destino, razão, artigos) |
| 05-9 | F3.4 | `WebhookSolucaoResponse` ganha `intencao`/`departamento_*`/`precisa_esclarecimento` |
| 10-7 | F3.4 | destino resolvido aplicado ao chat (`departamento_id`) |
| 00-8 | F3.4 (verificado) | status sai de `NOVO` via `ChatService.atualizar_status` |
| 01-4 | F3.5 | `PATCH /chats/{id}/confirmar-resolucao` leva `AGUARDANDO_CLIENTE` → `RESOLVIDO` |
| 01-11 | F3.5 | confirmação e reabertura explícitas (`confirmar-resolucao`, `reabrir`) |
| 05-4 | F3.5 (backend) / F4.11 (UI) | ciclo A fecha no backend; botão é a Task F4.11 |

**Fora desta fase:** `05-18` já foi fechado na Task F2.8 (`get_by_chat` devolve a última execução) e `03-18` (`/webhooks/chat/diagnostico` sem chamador) permanece ABERTO — está na lista de limpeza legada do README (§Gaps fora do escopo detalhado).

**Nota obrigatória de F3.1 (gap 02-10):** `ia_diagnosticos.status_ia` ganha o valor `ESCLARECIMENTO`. O bootstrap aditivo **não** propaga mudança de enum — atualizar o enum manualmente no Appwrite antes do deploy e registrar o passo no commit. O código e os testes passam sem isso.

---

### Task F3.1: Snapshot de diagnóstico no schema e status `ESCLARECIMENTO`

**Files:**
- Modify: `backend/app/appwrite/schema.py:47` (`STATUS_IA`) e `:174-186` (`ia_diagnosticos`)
- Modify: `backend/app/models/ia_diagnostico.py:10-13` (`StatusIA`)
- Test: `backend/tests/test_ia_diagnostico_schema.py`

**Interfaces:**
- Consumes: `text_attr`, `fk_attr`, `str_attr`, `float_attr`, `int_attr`, `enum_attr` (helpers existentes de `schema.py`).
- Produces:
  - `STATUS_IA = ["RESOLVIDO_PELA_IA", "TRANSFERIR_COM_SOLUCAO", "TRANSFERIR_SEM_SOLUCAO", "ESCLARECIMENTO"]`
  - `COLLECTIONS["ia_diagnosticos"]` com os sete atributos novos
  - `StatusIA.esclarecimento` em `app.models.ia_diagnostico`

**Decisão de armazenamento:** Appwrite não tem atributo JSON. `artigos_consultados` é `text` (string) contendo JSON serializado; o pipeline grava com `json.dumps` e quem lê desserializa. Documentado no docstring da coleção.

- [x] **Step 1: Write the failing test**

Create `backend/tests/test_ia_diagnostico_schema.py`:

```python
"""Snapshot do diagnostico no schema Appwrite (spec 02/05)."""

from app.appwrite import schema
from app.models.ia_diagnostico import StatusIA


def _attrs(col: str) -> dict[str, dict]:
    return {a["key"]: a for a in schema.COLLECTIONS[col]["attributes"]}


def test_diagnostico_guarda_a_classificacao_e_o_roteamento():
    attrs = _attrs("ia_diagnosticos")
    for chave in (
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_sugerido_codigo",
        "departamento_id",
        "motivo",
        "artigos_consultados",
    ):
        assert chave in attrs, f"atributo {chave} ausente"


def test_atributos_do_snapshot_sao_opcionais():
    attrs = _attrs("ia_diagnosticos")
    for chave in (
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_sugerido_codigo",
        "departamento_id",
        "motivo",
        "artigos_consultados",
    ):
        assert attrs[chave]["required"] is False


def test_artigos_consultados_e_texto_json():
    """Appwrite nao tem atributo JSON: guardamos JSON serializado em string."""
    attrs = _attrs("ia_diagnosticos")
    assert attrs["artigos_consultados"]["type"] == "string"
    assert attrs["artigos_consultados"]["size"] == schema.TEXT_SIZE


def test_departamento_id_tem_tamanho_de_ulid():
    assert _attrs("ia_diagnosticos")["departamento_id"]["size"] == 36


def test_status_ia_inclui_esclarecimento():
    assert "ESCLARECIMENTO" in schema.STATUS_IA
    assert StatusIA.esclarecimento.value == "ESCLARECIMENTO"


def test_status_ia_do_schema_espelha_o_enum():
    assert schema.STATUS_IA == [s.value for s in StatusIA]
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ia_diagnostico_schema.py -v`
Expected: FAIL — `AttributeError: type object 'StatusIA' has no attribute 'esclarecimento'` (e atributos ausentes)

- [x] **Step 3: Write minimal implementation**

Em `backend/app/models/ia_diagnostico.py`:

```python
class StatusIA(enum.StrEnum):
    resolvido_pela_ia = "RESOLVIDO_PELA_IA"
    transferir_com_solucao = "TRANSFERIR_COM_SOLUCAO"
    transferir_sem_solucao = "TRANSFERIR_SEM_SOLUCAO"
    esclarecimento = "ESCLARECIMENTO"
```

Em `backend/app/appwrite/schema.py`:

```python
from app.models.ia_diagnostico import StatusIA

STATUS_IA = [s.value for s in StatusIA]
```

(substitui a lista literal; o import dos models já é feito no topo do módulo)

```python
    "ia_diagnosticos": {
        "name": "IADiagnosticos",
        "attributes": [
            fk_attr("chat_id"),
            enum_attr("status_ia", STATUS_IA),
            text_attr("resumo"),
            text_attr("solucao"),
            text_attr("causa_provavel"),
            float_attr("confianca"),
            str_attr("modelo_usado", 100, required=False),
            int_attr("tokens_usados"),
            # Snapshot de roteamento (spec 05 §Persistência e eventos).
            # `artigos_consultados` é JSON serializado: Appwrite não tem tipo JSON.
            str_attr("intencao", 80, required=False),
            str_attr("subintencao", 100, required=False),
            str_attr("categoria_erp", 50, required=False),
            str_attr("departamento_sugerido_codigo", 80, required=False),
            fk_attr("departamento_id", required=False),
            text_attr("motivo"),
            text_attr("artigos_consultados"),
        ],
    },
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ia_diagnostico_schema.py -v`
Expected: PASS (6 testes)

- [x] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Expected: mesmo total do baseline de F0.1 + as tasks anteriores + 6.

- [x] **Step 6: Commit**

```bash
git add backend/app/appwrite/schema.py backend/app/models/ia_diagnostico.py backend/tests/test_ia_diagnostico_schema.py
git commit -m "feat(diagnostico): snapshot de intencao e roteamento no schema

- ia_diagnosticos guarda intencao, subintencao, categoria ERP,
  departamento sugerido/final, motivo e artigos consultados
- artigos_consultados e JSON serializado (Appwrite nao tem tipo JSON)
- StatusIA ganha ESCLARECIMENTO para o pedido de esclarecimento
- ATENCAO: mudanca de enum exige atualizacao manual no Appwrite (gap 02-10)"
```

- [x] **Step 7: Atualizar o Registro de Gaps (specs 02 e 05)**

Em `docs/specs/02-data-model.md`:

```
| 02-19 | `ia_diagnosticos` não guarda intenção, categoria ERP, departamento destino, artigos consultados nem razão | `appwrite/schema.py:174-186` | **Alta** | **CORRIGIDO** — `ia_diagnosticos` guarda `intencao`, `subintencao`, `categoria_erp`, `departamento_sugerido_codigo`, `departamento_id`, `motivo` e `artigos_consultados` (`appwrite/schema.py`) |
```

Em `docs/specs/05-ai-pipeline.md` (linha 05-23 fica **CORRIGIDO** só após F3.4; em F3.1 anotar parcial):

```
| 05-23 | Diagnóstico não persiste intenção/departamento/artigos consultados/razão | `services/ai_pipeline.py`; `appwrite/schema.py` | **Alta** | **CORRIGIDO (schema)** — atributos do snapshot criados em `appwrite/schema.py`; gravação na Task F3.4 |
```

---

### Task F3.2: Pipeline classifica antes do RAG e trata os casos sem busca

**Files:**
- Modify: `backend/app/services/ai_pipeline.py:20-82`
- Modify: `backend/tests/test_ai_pipeline.py` (`FakeEmbedder` com contador, `_stub_ai` injeta classificador, fixture semeia departamentos)
- Test: `backend/tests/test_ai_pipeline_intencao.py`

**Interfaces:**
- Consumes: `IntentClassifier.classificar(texto) -> ClassificacaoIntencao` (F2.2), `RoutingService.resolver(...) -> ResultadoRoteamento` (F2.4), `PERGUNTA_ESCLARECIMENTO` (F2.1).
- Produces:
  - `AIPipelineService._classificar(texto) -> ClassificacaoIntencao`
  - `AIPipelineService._rotear(classificacao, chat) -> ResultadoRoteamento`
  - `MSG_ENCAMINHAMENTO: str` (resposta quando a intenção não é técnica)
  - `_INTENCOES_COM_RAG = frozenset({Intencao.problema_tecnico, Intencao.duvida_uso_erp})`
  - `_STATUS_FINAL[StatusIA.esclarecimento] = StatusChat.aguardando_cliente`

**Regra da spec 05 §Etapas 5:** RAG técnico só para `problema_tecnico` e `duvida_uso_erp`. Pedido de humano, financeiro, comercial, administrativo, implantação e dúvida geral **não** consomem RAG.

**Regra de esclarecimento:** quando o resolver devolve `precisa_esclarecimento=True`, o chat vai para `AGUARDANDO_CLIENTE` (a IA está esperando a resposta) e a mensagem é a pergunta do classificador. Não há transferência e nenhum diagnóstico conclusivo é registrado.

- [x] **Step 1: Write the failing test**

Create `backend/tests/test_ai_pipeline_intencao.py`:

```python
"""O pipeline classifica antes do RAG e pula a busca quando nao e tecnico."""

import pytest

from app.core.config import settings
from app.services import qdrant_service
from app.services.ai_pipeline import MSG_ENCAMINHAMENTO, NO_HIT_MENSAGEM
from app.services.departamento_seed import semear

TECNICA = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "Falha ao emitir NF-e.",
}

FINANCEIRA = {
    **TECNICA,
    "intencao": "solicitacao_financeira",
    "subintencao": "negociacao",
    "categoria_erp": None,
    "departamento_sugerido_codigo": "financeiro",
    "confianca": 0.96,
    "motivo": "Cliente quer negociar mensalidade.",
}

AMBIGUA = {
    **TECNICA,
    "intencao": "intencao_desconhecida",
    "subintencao": None,
    "categoria_erp": None,
    "departamento_sugerido_codigo": None,
    "confianca": 0.2,
    "precisa_esclarecimento": True,
    "pergunta_esclarecimento": "É um problema no sistema ou uma questão financeira?",
}


class FakeLLM:
    def __init__(self, payload: dict):
        self.model = "fake-model"
        self.payload = payload
        self.chamadas: list = []

    async def chat_json(self, messages, temperature: float = 0.3):
        self.chamadas.append(messages)
        return self.payload


class ContadorEmbedder:
    def __init__(self):
        self.chamadas = 0

    async def embed(self, texto: str):
        self.chamadas += 1
        return [0.1] * 768


HITS = [
    {
        "id": "artigo-1",
        "score": 0.92,
        "titulo": "Erro na emissão de NF-e",
        "conteudo": "Acesse o módulo fiscal.",
        "categoria": "fiscal",
    }
]

SOLUCAO_PRONTA = {
    "solucao": None,
    "instrucoes_cliente": None,
    "precisa_humano": True,
    "referencia": None,
    "confianca": 0.2,
}


def _stub(monkeypatch, classificacao: dict, embedder: ContadorEmbedder, hits: list[dict]):
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm", lambda: FakeLLM(classificacao)
    )
    monkeypatch.setattr(
        "app.services.ai_pipeline.get_llm", lambda: FakeLLM(SOLUCAO_PRONTA)
    )
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: embedder)

    async def _search(embedding, limit: int = 5):
        return hits

    monkeypatch.setattr(qdrant_service, "search_similar", _search)


@pytest.fixture
async def chat(fake_repos):
    await semear(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "remetente": "cliente",
            "tipo": "texto",
            "conteudo": "Quero negociar minha mensalidade",
        }
    )
    return chat


async def _solucionar(client, chat_id: str):
    return await client.post(
        "/webhooks/ai/solucionar",
        json={"chat_id": chat_id},
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )


@pytest.mark.asyncio
async def test_intencao_nao_tecnica_nao_consome_rag(
    client, fake_repos, chat, monkeypatch
):
    embedder = ContadorEmbedder()
    _stub(monkeypatch, FINANCEIRA, embedder, HITS)

    resp = await _solucionar(client, chat["id"])

    assert resp.status_code == 200
    assert resp.json()["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert resp.json()["mensagem_cliente"] == MSG_ENCAMINHAMENTO
    assert embedder.chamadas == 0


@pytest.mark.asyncio
async def test_intencao_tecnica_consome_rag(client, fake_repos, chat, monkeypatch):
    embedder = ContadorEmbedder()
    _stub(monkeypatch, TECNICA, embedder, HITS)

    resp = await _solucionar(client, chat["id"])

    assert resp.status_code == 200
    assert embedder.chamadas == 1
    assert resp.json()["status_ia"] in ("RESOLVIDO_PELA_IA", "TRANSFERIR_COM_SOLUCAO")


@pytest.mark.asyncio
async def test_baixa_confianca_pede_esclarecimento_e_nao_transfere(
    client, fake_repos, chat, monkeypatch
):
    embedder = ContadorEmbedder()
    _stub(monkeypatch, AMBIGUA, embedder, HITS)

    resp = await _solucionar(client, chat["id"])

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["status_ia"] == "ESCLARECIMENTO"
    assert corpo["chat_status"] == "AGUARDANDO_CLIENTE"
    assert corpo["mensagem_cliente"] == AMBIGUA["pergunta_esclarecimento"]
    assert corpo["precisa_humano"] is False
    assert embedder.chamadas == 0

    chat_db = await fake_repos.chats.get(chat["id"])
    assert chat_db["status"] == "AGUARDANDO_CLIENTE"


@pytest.mark.asyncio
async def test_esclarecimento_nao_marca_departamento(
    client, fake_repos, chat, monkeypatch
):
    _stub(monkeypatch, AMBIGUA, ContadorEmbedder(), HITS)
    await _solucionar(client, chat["id"])
    chat_db = await fake_repos.chats.get(chat["id"])
    assert chat_db["departamento_id"] is None


@pytest.mark.asyncio
async def test_pedido_de_humano_nao_consome_rag(
    client, fake_repos, chat, monkeypatch
):
    humano = {
        **TECNICA,
        "intencao": "solicitacao_humano",
        "subintencao": None,
        "categoria_erp": None,
        "confianca": 0.97,
    }
    embedder = ContadorEmbedder()
    _stub(monkeypatch, humano, embedder, HITS)

    resp = await _solucionar(client, chat["id"])

    assert resp.status_code == 200
    assert embedder.chamadas == 0
    assert resp.json()["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"


@pytest.mark.asyncio
async def test_no_hit_continua_respondendo_sem_llm(
    client, fake_repos, chat, monkeypatch
):
    _stub(monkeypatch, TECNICA, ContadorEmbedder(), [])
    resp = await _solucionar(client, chat["id"])
    assert resp.status_code == 200
    assert resp.json()["mensagem_cliente"] == NO_HIT_MENSAGEM
    assert resp.json()["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ai_pipeline_intencao.py -v`
Expected: FAIL — `ImportError: cannot import name 'MSG_ENCAMINHAMENTO' from 'app.services.ai_pipeline'`

- [x] **Step 3: Write minimal implementation**

Em `backend/app/services/ai_pipeline.py`, imports e constantes:

```python
import json

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.ai.intent_classifier import IntentClassifier
from app.ai.prompts import build_solution_messages
from app.ai.provider import LLMIndisponivelError, get_embedder, get_llm
from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.models.departamento import Intencao
from app.models.ia_diagnostico import StatusIA
from app.schemas.ai import PERGUNTA_ESCLARECIMENTO
from app.services import qdrant_service
from app.services.chat_service import ChatService
from app.services.routing_service import RoutingService
```

```python
MSG_ENCAMINHAMENTO = (
    "Entendi a sua solicitação e já encaminhei para a equipe responsável. "
    "Em breve alguém falará com você por aqui."
)

_INTENCOES_COM_RAG = frozenset({Intencao.problema_tecnico, Intencao.duvida_uso_erp})
```

```python
_STATUS_FINAL = {
    StatusIA.resolvido_pela_ia: StatusChat.aguardando_cliente,
    StatusIA.transferir_com_solucao: StatusChat.aguardando_humano_com_solucao,
    StatusIA.transferir_sem_solucao: StatusChat.aguardando_humano_sem_solucao,
    StatusIA.esclarecimento: StatusChat.aguardando_cliente,
}
```

Em `solucionar`, substituir o trecho a partir de `historico = ...`:

```python
        historico = await self._historico(chat_id)
        client_msgs = [m for m in historico if m["remetente"] == "cliente"]
        if not client_msgs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat não possui mensagens do cliente",
            )
        ultima = client_msgs[-1]
        classificacao = await self._classificar(ultima["conteudo"])
        roteamento = await self._rotear(classificacao, chat)

        if roteamento.precisa_esclarecimento:
            return await self._finalizar(
                chat_id,
                StatusIA.esclarecimento,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=(
                    roteamento.pergunta_esclarecimento or PERGUNTA_ESCLARECIMENTO
                ),
            )

        if classificacao.intencao not in _INTENCOES_COM_RAG:
            return await self._finalizar(
                chat_id,
                StatusIA.transferir_sem_solucao,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=MSG_ENCAMINHAMENTO,
            )

        hits = await self._buscar_base(ultima["conteudo"])
        if not hits:
            return await self._finalizar(
                chat_id,
                StatusIA.transferir_sem_solucao,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=NO_HIT_MENSAGEM,
            )

        return await self._resolver_llm(chat_id, hits, ultima["conteudo"], historico)
```

E os dois métodos novos:

```python
    async def _classificar(self, texto: str):
        """Classificação é sugestão; falha de contrato vira inconclusiva."""
        return await IntentClassifier().classificar(texto)

    async def _rotear(self, classificacao, chat: dict):
        return await RoutingService(self.repos).resolver(
            classificacao,
            departamento_atual_id=chat.get("departamento_id"),
        )
```

Modify `backend/tests/test_ai_pipeline.py` — `FakeEmbedder` ganha contador e `_stub_ai` injeta o classificador:

```python
class FakeEmbedder:
    def __init__(self, falha: bool = False):
        self.falha = falha
        self.chamadas = 0

    async def embed(self, texto: str):
        self.chamadas += 1
        if self.falha:
            raise RuntimeError("embedding indisponível")
        return [0.1] * 768
```

```python
CLASSIFICACAO_TECNICA = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "Falha ao emitir NF-e.",
}


def _stub_ai(monkeypatch, llm: FakeLLM, embedder: FakeEmbedder, hits: list[dict]):
    monkeypatch.setattr("app.services.ai_pipeline.get_llm", lambda: llm)
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: embedder)
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm",
        lambda: FakeLLM(CLASSIFICACAO_TECNICA),
    )

    async def _search(embedding, limit: int = 5):
        return hits

    monkeypatch.setattr(qdrant_service, "search_similar", _search)
```

E na fixture `chat_com_mensagem` (hoje em `backend/tests/test_ai_pipeline.py:44-57`), semear os departamentos antes de criar o chat:

```python
from app.services.departamento_seed import semear

@pytest.fixture
async def chat_com_mensagem(fake_repos):
    await semear(fake_repos)
    suporte = await fake_repos.departamentos.get_by_codigo("suporte_tecnico")
    chat = await fake_repos.chats.create(
        {
            "whatsapp_number": "5511999990000",
            "status": "NOVO",
            "departamento_id": suporte["id"],
        }
    )
    await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "remetente": "cliente",
            "tipo": "texto",
            "conteudo": "Minha NF-e não está emitindo",
        }
    )
    return chat
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ai_pipeline_intencao.py tests/test_ai_pipeline.py -v`
Expected: PASS (6 testes novos + os 8 existentes)

- [x] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [x] **Step 6: Commit**

```bash
git add backend/app/services/ai_pipeline.py backend/tests/test_ai_pipeline.py backend/tests/test_ai_pipeline_intencao.py
git commit -m "feat(diagnostico): pipeline classifica a intencao antes do RAG

- intencao nao tecnica nao consome busca na base (spec 05 etapa 5)
- baixa confianca vai para ESCLARECIMENTO/AGUARDANDO_CLIENTE
- pedido de humano encerra a automacao sem RAG
- testes injetam o classificador via monkeypatch, sem rede"
```

- [x] **Step 7: Atualizar o Registro de Gaps (spec 05 e 01)**

```
| 05-21 | Classificação de intenção não separa categoria ERP de departamento; `CLASSIFY_SYSTEM` só devolve categoria | `ai/prompts.py` | **Alta** | **CORRIGIDO** — pipeline usa `IntentClassifier` (intenção, categoria ERP) e `RoutingService` (departamento) como dimensões distintas |
```

---

### Task F3.3: RAG filtrado por categoria ERP, limiar de relevância e artigos consultados

**Files:**
- Modify: `backend/app/services/qdrant_service.py:32-52` (`search_similar`)
- Modify: `backend/app/core/config.py:34-42` (novo `rag_min_score`)
- Modify: `backend/app/services/ai_pipeline.py` (`_buscar_base` recebe categoria e aplica limiar)
- Modify: `backend/tests/test_ai_pipeline.py` (`_search` aceita `categoria`)
- Test: `backend/tests/test_rag_categoria.py`

**Interfaces:**
- Consumes: `CategoriaERP` (F1.1), `settings` (F2.3).
- Produces:
  - `qdrant_service.search_similar(query_embedding, limit=5, categoria: str | None = None) -> list[dict]`
  - `settings.rag_min_score: float` (padrão `0.35`, `0 <= x <= 1`)
  - `AIPipelineService._buscar_base(texto: str, categoria: str | None) -> list[dict]` — devolve só hits com `score >= rag_min_score`

**Regra da spec 05 §RAG 1–3:** filtrar artigos ativos e, quando possível, pela `categoria_erp`; não assumir que top-k significa evidência — aplicar limiar configurável.

- [x] **Step 1: Write the failing test**

Create `backend/tests/test_rag_categoria.py`:

```python
"""Filtro por categoria ERP e limiar minimo de relevancia no RAG."""

import types

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.services import qdrant_service


class FakeQdrant:
    def __init__(self):
        self.kwargs: dict | None = None

    def query_points(self, **kwargs):
        self.kwargs = kwargs
        ponto = types.SimpleNamespace(
            id="ponto-1",
            score=0.9,
            payload={
                "article_id": "a1",
                "titulo": "Erro na NF-e",
                "conteudo": "Acesse fiscal.",
                "categoria": "fiscal",
            },
        )
        return types.SimpleNamespace(points=[ponto])


def test_busca_com_categoria_aplica_filtro(monkeypatch):
    fake = FakeQdrant()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    import asyncio

    hits = asyncio.run(
        qdrant_service.search_similar([0.1] * 768, limit=5, categoria="fiscal")
    )

    condicao = fake.kwargs["query_filter"].must[0]
    assert condicao.key == "categoria"
    assert condicao.match.value == "fiscal"
    assert hits[0]["categoria"] == "fiscal"


def test_busca_sem_categoria_nao_filtra(monkeypatch):
    fake = FakeQdrant()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    import asyncio

    asyncio.run(qdrant_service.search_similar([0.1] * 768, limit=5))

    assert fake.kwargs.get("query_filter") is None


def test_limiar_de_relevancia_tem_default_da_spec():
    assert Settings().rag_min_score == 0.35


def test_limiar_fora_de_0_1_e_invalido():
    with pytest.raises(ValidationError):
        Settings(rag_min_score=1.5)


@pytest.mark.asyncio
async def test_hit_abaixo_do_limiar_vira_sem_solucao(
    client, fake_repos, monkeypatch
):
    """Nenhum hit confiavel: cenario C sem chamar o LLM de solucao."""
    from app.services.ai_pipeline import NO_HIT_MENSAGEM
    from app.services.departamento_seed import semear

    await semear(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "remetente": "cliente",
            "tipo": "texto",
            "conteudo": "Minha NF-e não emite",
        }
    )

    from tests.test_ai_pipeline import CLASSIFICACAO_TECNICA, FakeLLM

    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm",
        lambda: FakeLLM(CLASSIFICACAO_TECNICA),
    )

    chamadas = {"llm": 0}

    class LLMContado(FakeLLM):
        async def chat_json(self, messages, temperature: float = 0.3):
            chamadas["llm"] += 1
            return await super().chat_json(messages, temperature)

    monkeypatch.setattr(
        "app.services.ai_pipeline.get_llm", lambda: LLMContado({"solucao": "x"})
    )

    class Embedder:
        async def embed(self, texto):
            return [0.1] * 768

    monkeypatch.setattr(
        "app.services.ai_pipeline.get_embedder", lambda: Embedder()
    )

    async def _search(embedding, limit: int = 5, categoria: str | None = None):
        return [{"id": "a1", "score": 0.10, "titulo": "irrelevante",
                 "conteudo": "nada a ver", "categoria": "fiscal"}]

    monkeypatch.setattr(qdrant_service, "search_similar", _search)

    resp = await client.post(
        "/webhooks/ai/solucionar",
        json={"chat_id": chat["id"]},
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )

    assert resp.status_code == 200
    assert resp.json()["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert resp.json()["mensagem_cliente"] == NO_HIT_MENSAGEM
    assert chamadas["llm"] == 0
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_rag_categoria.py -v`
Expected: FAIL — `TypeError: search_similar() got an unexpected keyword argument 'categoria'` e `AttributeError: 'Settings' object has no attribute 'rag_min_score'`

- [x] **Step 3: Write minimal implementation**

Em `backend/app/core/config.py`:

```python
    # RAG tecnico (docs/specs/05-ai-pipeline.md §Pipeline RAG tecnico)
    rag_min_score: float = Field(default=0.35, ge=0.0, le=1.0)
```

Em `backend/app/services/qdrant_service.py`:

```python
async def search_similar(
    query_embedding: list[float],
    limit: int = 5,
    categoria: str | None = None,
) -> list[dict]:
    client = get_qdrant()
    query_filter = None
    if categoria:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="categoria", match=models.MatchValue(value=categoria)
                )
            ]
        )
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    hits = response.points
    return [
        {
            "id": (h.payload or {}).get("article_id", str(h.id)),
            "score": h.score,
            "titulo": (h.payload or {}).get("titulo", ""),
            "conteudo": (h.payload or {}).get("conteudo", ""),
            "categoria": (h.payload or {}).get("categoria", ""),
        }
        for h in hits
    ]
```

Em `backend/app/services/ai_pipeline.py`:

```python
    async def _buscar_base(
        self, texto: str, categoria: str | None = None
    ) -> list[dict]:
        try:
            embedding = await get_embedder().embed(texto)
            hits = await qdrant_service.search_similar(
                embedding, limit=5, categoria=categoria
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Busca na base de conhecimento indisponível",
            )
        return [h for h in hits if (h.get("score") or 0) >= settings.rag_min_score]
```

e o chamador passa a categoria:

```python
        categoria_erp = (
            classificacao.categoria_erp.value if classificacao.categoria_erp else None
        )
        hits = await self._buscar_base(ultima["conteudo"], categoria_erp)
```

Em `backend/tests/test_ai_pipeline.py`, `_search` ganha o parâmetro:

```python
    async def _search(embedding, limit: int = 5, categoria: str | None = None):
        return hits
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_rag_categoria.py tests/test_ai_pipeline.py -v`
Expected: PASS (5 testes novos + os existentes)

- [x] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [x] **Step 6: Commit**

```bash
git add backend/app/services/qdrant_service.py backend/app/core/config.py backend/app/services/ai_pipeline.py backend/tests/test_ai_pipeline.py backend/tests/test_rag_categoria.py
git commit -m "feat(rag): filtro por categoria ERP e limiar minimo de relevancia

- search_similar aceita categoria e monta filtro no Qdrant
- RAG_MIN_SCORE=0.35 descarta hit irrelevante (spec 05 §RAG 3)
- pipeline sem hit confiavel cai no cenario C sem chamar o LLM"
```

- [x] **Step 7: Atualizar o Registro de Gaps (specs 05 e 08)**

```
| 05-23 | Diagnóstico não persiste intenção/departamento/artigos consultados/razão | `services/ai_pipeline.py`; `appwrite/schema.py` | **Alta** | **CORRIGIDO (parcial)** — categoria ERP filtra o RAG e o limiar de relevância é aplicado; snapshot completo na Task F3.4 |
| 08-6 | Sem métricas/tracing/APM; nenhum SLO observável | `app/**` | Média | **ABERTO (parcial)** — limiar de relevância do RAG é configurável e testado; APM/SLO seguem na Trilha R1 |
```

---

### Task F3.4: Snapshot completo no diagnóstico e destino aplicado ao chat

**Files:**
- Modify: `backend/app/services/ai_pipeline.py:34-42,176-230` (`SolucaoLLM` intacto; `_finalizar` e o retorno)
- Modify: `backend/app/schemas/webhook.py:57-67` (`WebhookSolucaoResponse`)
- Test: `backend/tests/test_ai_pipeline_roteamento.py`

**Interfaces:**
- Consumes: `ClassificacaoIntencao` (F2.1), `ResultadoRoteamento` (F2.4), atributos de F3.1.
- Produces:
  - `AIPipelineService._finalizar(..., classificacao=None, roteamento=None, artigos=None)`
  - `WebhookSolucaoResponse` com `intencao`, `departamento_id`, `departamento_codigo`, `precisa_esclarecimento`
  - `chats.departamento_id` aplicado apenas nos cenários B e C

**Regra:** o chat recebe `departamento_id` **somente** quando o resultado é transferência (`TRANSFERIR_COM_SOLUCAO`/`TRANSFERIR_SEM_SOLUCAO`). No cenário A o chat segue com a IA e o departamento não é preenchido. O `departamento_sugerido_codigo` do LLM é registrado mas **nunca** usado como destino (C8).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ai_pipeline_roteamento.py`:

```python
"""Snapshot de roteamento gravado no diagnostico e aplicado ao chat."""

import json

import pytest

from app.core.config import settings
from app.services import qdrant_service
from app.services.departamento_seed import semear

TECNICA = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "Falha ao emitir NF-e.",
}

HITS = [
    {
        "id": "artigo-1",
        "score": 0.93,
        "titulo": "Erro na emissão de NF-e",
        "conteudo": "Acesse o módulo fiscal.",
        "categoria": "fiscal",
    }
]


class FakeLLM:
    def __init__(self, payload: dict):
        self.model = "fake-model"
        self.payload = payload
        self.chamadas = []

    async def chat_json(self, messages, temperature: float = 0.3):
        self.chamadas.append(messages)
        return self.payload


class Embedder:
    async def embed(self, texto):
        return [0.1] * 768


def _stub(monkeypatch, solucao: dict, classificacao: dict | None = None):
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm",
        lambda: FakeLLM(classificacao or TECNICA),
    )
    monkeypatch.setattr(
        "app.services.ai_pipeline.get_llm", lambda: FakeLLM(solucao)
    )
    monkeypatch.setattr(
        "app.services.ai_pipeline.get_embedder", lambda: Embedder()
    )

    async def _search(embedding, limit: int = 5, categoria: str | None = None):
        return HITS

    monkeypatch.setattr(qdrant_service, "search_similar", _search)


@pytest.fixture
async def chat_com_regra(fake_repos):
    """Uma regra explicita manda problema_tecnico+fiscal para suporte_tecnico."""
    await semear(fake_repos)
    suporte = await fake_repos.departamentos.get_by_codigo("suporte_tecnico")
    await fake_repos.regras_roteamento.create(
        {
            "intencao": "problema_tecnico",
            "categoria_erp": "fiscal",
            "departamento_id": suporte["id"],
            "prioridade_regra": 10,
            "ativo": True,
        }
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "remetente": "cliente",
            "tipo": "texto",
            "conteudo": "Minha NF-e não emite",
        }
    )
    return chat, suporte


async def _solucionar(client, chat_id: str):
    return await client.post(
        "/webhooks/ai/solucionar",
        json={"chat_id": chat_id},
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )


SOLUCAO_RESOLVE = {
    "solucao": "Reenvie a NF-e pelo módulo fiscal",
    "instrucoes_cliente": None,
    "precisa_humano": False,
    "referencia": "Erro na emissão de NF-e",
    "confianca": 0.92,
}

SOLUCAO_HUMANO = {
    "solucao": "Ajuste de parâmetro fiscal pelo suporte",
    "instrucoes_cliente": "Envie o print do erro",
    "precisa_humano": True,
    "referencia": "Erro na emissão de NF-e",
    "confianca": 0.7,
}

SOLUCAO_VAZIA = {
    "solucao": None,
    "instrucoes_cliente": "Envie o print do erro",
    "precisa_humano": True,
    "referencia": None,
    "confianca": 0.1,
}


@pytest.mark.asyncio
async def test_cenario_b_grava_snapshot_e_aplica_departamento(
    client, fake_repos, chat_com_regra, monkeypatch
):
    chat, suporte = chat_com_regra
    _stub(monkeypatch, SOLUCAO_HUMANO)

    resp = await _solucionar(client, chat["id"])

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["status_ia"] == "TRANSFERIR_COM_SOLUCAO"
    assert corpo["intencao"] == "problema_tecnico"
    assert corpo["departamento_codigo"] == "suporte_tecnico"
    assert corpo["precisa_esclarecimento"] is False

    chat_db = await fake_repos.chats.get(chat["id"])
    assert chat_db["status"] == "AGUARDANDO_HUMANO_COM_SOLUCAO"
    assert chat_db["departamento_id"] == suporte["id"]

    diagnostico = (await fake_repos.ia_diagnosticos.list_all())[0]
    assert diagnostico["intencao"] == "problema_tecnico"
    assert diagnostico["subintencao"] == "emissao_nfe"
    assert diagnostico["categoria_erp"] == "fiscal"
    assert diagnostico["departamento_sugerido_codigo"] == "suporte_tecnico"
    assert diagnostico["departamento_id"] == suporte["id"]
    assert diagnostico["motivo"]
    artigos = json.loads(diagnostico["artigos_consultados"])
    assert artigos[0]["id"] == "artigo-1"
    assert artigos[0]["score"] == 0.93


@pytest.mark.asyncio
async def test_cenario_a_nao_aplica_departamento(
    client, fake_repos, chat_com_regra, monkeypatch
):
    chat, _ = chat_com_regra
    _stub(monkeypatch, SOLUCAO_RESOLVE)

    resp = await _solucionar(client, chat["id"])

    corpo = resp.json()
    assert corpo["status_ia"] == "RESOLVIDO_PELA_IA"
    assert corpo["departamento_id"] is None
    chat_db = await fake_repos.chats.get(chat["id"])
    assert chat_db["status"] == "AGUARDANDO_CLIENTE"
    assert chat_db["departamento_id"] is None


@pytest.mark.asyncio
async def test_cenario_c_cai_no_fallback_e_aplica_o_departamento(
    client, fake_repos, chat_com_regra, monkeypatch
):
    chat, _ = chat_com_regra
    _stub(monkeypatch, SOLUCAO_VAZIA)

    resp = await _solucionar(client, chat["id"])

    corpo = resp.json()
    assert corpo["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert corpo["departamento_codigo"] == "suporte_tecnico"
    chat_db = await fake_repos.chats.get(chat["id"])
    assert chat_db["status"] == "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    assert chat_db["departamento_id"] is not None


@pytest.mark.asyncio
async def test_intencao_sem_regra_usa_atendimento_geral(
    client, fake_repos, chat_com_regra, monkeypatch
):
    chat, _ = chat_com_regra
    await semear(fake_repos)
    geral = await fake_repos.departamentos.get_by_codigo("atendimento_geral")
    administrativa = {
        **TECNICA,
        "intencao": "solicitacao_administrativa",
        "subintencao": None,
        "categoria_erp": None,
        "departamento_sugerido_codigo": "administrativo",
    }
    _stub(monkeypatch, SOLUCAO_VAZIA, administrativa)

    resp = await _solucionar(client, chat["id"])

    corpo = resp.json()
    assert corpo["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert corpo["departamento_codigo"] == "atendimento_geral"
    assert (await fake_repos.chats.get(chat["id"]))["departamento_id"] == geral["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ai_pipeline_roteamento.py -v`
Expected: FAIL — `KeyError: 'intencao'` na resposta e `chats.departamento_id` permanece `None`

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/ai_pipeline.py`, atualizar as três chamadas de `_finalizar` para passar contexto:

```python
        return await self._finalizar(
            chat_id,
            status_ia,
            campos_ia=campos_ia,
            categoria=hits[0].get("categoria") or None,
            mensagem_cliente=mensagem_cliente.strip(),
            classificacao=classificacao,
            roteamento=roteamento,
            artigos=hits,
            modelo_usado=llm.model,
            referencia=solucao.referencia,
            instrucoes_cliente=solucao.instrucoes_cliente,
        )
```

(como `_resolver_llm` não recebe `classificacao`/`roteamento`, adicionar ambos à assinatura de `_resolver_llm` e passá-los em `solucionar`)

```python
    async def _resolver_llm(
        self,
        chat_id: str,
        hits: list[dict],
        mensagem: str,
        historico: list[dict],
        classificacao=None,
        roteamento=None,
    ) -> dict:
```

E em `solucionar`:

```python
        return await self._resolver_llm(
            chat_id, hits, ultima["conteudo"], historico, classificacao, roteamento
        )
```

Nova assinatura e corpo de `_finalizar`:

```python
    async def _finalizar(
        self,
        chat_id: str,
        status_ia: StatusIA,
        campos_ia: dict | None,
        categoria: str | None,
        mensagem_cliente: str,
        classificacao=None,
        roteamento=None,
        artigos: list[dict] | None = None,
        modelo_usado: str | None = None,
        referencia: str | None = None,
        instrucoes_cliente: str | None = None,
    ) -> dict:
        departamento_id = (
            roteamento.departamento_id if roteamento is not None else None
        )
        intencao = classificacao.intencao.value if classificacao else None
        categoria_erp = (
            classificacao.categoria_erp.value
            if classificacao and classificacao.categoria_erp
            else None
        )
        await self.repos.ia_diagnosticos.create(
            {
                "chat_id": chat_id,
                "status_ia": status_ia.value,
                "resumo": (campos_ia or {}).get("resumo"),
                "solucao": (campos_ia or {}).get("solucao"),
                "causa_provavel": (campos_ia or {}).get("causa_provavel"),
                "confianca": (campos_ia or {}).get("confianca"),
                "modelo_usado": modelo_usado,
                "tokens_usados": None,
                "intencao": intencao,
                "subintencao": classificacao.subintencao if classificacao else None,
                "categoria_erp": categoria_erp,
                "departamento_sugerido_codigo": (
                    classificacao.departamento_sugerido_codigo
                    if classificacao
                    else None
                ),
                "departamento_id": departamento_id,
                "motivo": roteamento.motivo if roteamento is not None else None,
                "artigos_consultados": (
                    json.dumps(
                        [
                            {
                                "id": h.get("id"),
                                "titulo": h.get("titulo"),
                                "score": h.get("score"),
                                "categoria": h.get("categoria"),
                            }
                            for h in artigos
                        ],
                        ensure_ascii=False,
                    )
                    if artigos
                    else None
                ),
            }
        )

        chat = await self.chats.atualizar_status(chat_id, _STATUS_FINAL[status_ia])
        espelho = {
            "solucao_sugerida_ia": (campos_ia or {}).get("solucao"),
            "nivel_confianca_ia": (campos_ia or {}).get("confianca"),
            "necessita_humano": status_ia
            in (StatusIA.transferir_com_solucao, StatusIA.transferir_sem_solucao),
            "resumo_problema": (campos_ia or {}).get("resumo"),
            "causa_provavel": (campos_ia or {}).get("causa_provavel"),
        }
        if departamento_id and status_ia != StatusIA.resolvido_pela_ia:
            espelho["departamento_id"] = departamento_id
        await self.repos.chats.update(chat_id, espelho)

        return {
            "chat_id": chat_id,
            "status_ia": status_ia.value,
            "categoria": categoria,
            "solucao": (campos_ia or {}).get("solucao"),
            "instrucoes_cliente": instrucoes_cliente,
            "precisa_humano": status_ia
            in (StatusIA.transferir_com_solucao, StatusIA.transferir_sem_solucao),
            "referencia": referencia,
            "confianca": (campos_ia or {}).get("confianca"),
            "mensagem_cliente": mensagem_cliente,
            "chat_status": chat["status"],
            "intencao": intencao,
            "departamento_id": departamento_id,
            "departamento_codigo": (
                roteamento.departamento_codigo if roteamento is not None else None
            ),
            "precisa_esclarecimento": (
                roteamento.precisa_esclarecimento if roteamento is not None else False
            ),
        }
```

> `necessita_humano` para `ESCLARECIMENTO` passa a ser `False` (é a IA esperando o cliente, não um transbordo). Isso está coberto por `test_baixa_confianca_pede_esclarecimento_e_nao_transfere`.

Em `backend/app/schemas/webhook.py`:

```python
class WebhookSolucaoResponse(BaseModel):
    chat_id: str
    status_ia: StatusIA
    categoria: str | None = None
    solucao: str | None = None
    instrucoes_cliente: str | None = None
    precisa_humano: bool
    referencia: str | None = None
    confianca: float | None = None
    mensagem_cliente: str
    chat_status: StatusChat
    intencao: str | None = None
    departamento_id: str | None = None
    departamento_codigo: str | None = None
    precisa_esclarecimento: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ai_pipeline_roteamento.py tests/test_ai_pipeline.py tests/test_ai_pipeline_intencao.py -v`
Expected: PASS (4 novos + os existentes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ai_pipeline.py backend/app/schemas/webhook.py backend/tests/test_ai_pipeline_roteamento.py
git commit -m "feat(diagnostico): snapshot completo e destino aplicado ao chat

- diagnostico grava intencao, categoria ERP, destino sugerido/final,
  motivo e artigos consultados (JSON)
- departamento_id so e aplicado em cenarios B/C; cenario A fica com a IA
- resposta do webhook expoe intencao, departamento e esclarecimento"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 05, 10, 02 e 00)**

```
| 05-23 | Diagnóstico não persiste intenção/departamento/artigos consultados/razão | `services/ai_pipeline.py`; `appwrite/schema.py` | **Alta** | **CORRIGIDO** — `_finalizar` grava intenção, categoria ERP, destino sugerido/final, motivo e artigos (`services/ai_pipeline.py`) |
| 10-7 | `/chats/{id}/roteamento` (resolver determinístico) inexistente | `api/routes/` | **Alta** | **CORRIGIDO** — destino resolvido por `RoutingService` é aplicado em `chats.departamento_id` pelo pipeline |
```

```
| 00-8 | Status do chat nunca saía de `NOVO` no fluxo real | `services/ai_pipeline.py` | **Crítica** | **CORRIGIDO (verificado)** — `_finalizar` transita via `ChatService.atualizar_status`; teste `test_cenario_b_grava_snapshot_e_aplica_departamento` |
```

---

### Task F3.5: Confirmação de resolução e reabertura (cenário A)

**Files:**
- Modify: `backend/app/services/chat_service.py` (novos `confirmar_resolucao` e `reabrir`)
- Modify: `backend/app/services/webhook_service.py:60-75` (reabertura ao receber mensagem do cliente)
- Modify: `backend/app/api/routes/chats.py` (duas rotas novas)
- Test: `backend/tests/test_ciclo_resolucao.py`

**Interfaces:**
- Consumes: `ChatService.obter`, `pode_ver_chat` (F1.10), `StatusChat`/`STATUS_TRANSITIONS`.
- Produces:
  - `ChatService.confirmar_resolucao(chat_id: str, user: dict) -> dict` — `AGUARDANDO_CLIENTE` → `RESOLVIDO`; 409 fora desse estado
  - `ChatService.reabrir(chat_id: str, user: dict, motivo: str | None = None) -> dict` — `RESOLVIDO`/`AGUARDANDO_CLIENTE` → `IA_ANALISANDO`; 409 fora desses estados
  - `PATCH /chats/{chat_id}/confirmar-resolucao` e `PATCH /chats/{chat_id}/reabrir`
  - `WebhookService.receber_mensagem` reabre chat `RESOLVIDO` quando chega mensagem do cliente

**Regra (spec 04):** atendente só confirma/reabre chats em que é o responsável; admin e supervisor podem em qualquer chat do escopo.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ciclo_resolucao.py`:

```python
"""Confirmacao de resolucao e reabertura do cenario A (spec 05/01)."""

import pytest

from app.core.config import settings


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _chat(fake_repos, status: str, atendente_id: str | None = None):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": status,
            "atendente_id": atendente_id,
        }
    )


@pytest.mark.asyncio
async def test_admin_confirma_resolucao(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVIDO"


@pytest.mark.asyncio
async def test_confirmar_fora_de_aguardando_cliente_retorna_409(
    client, admin_token, fake_repos
):
    chat = await _chat(fake_repos, "NOVO")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(admin_token)
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_atendente_so_confirma_chat_proprio(client, atendente_token, fake_repos):
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE", atendente_id="outro")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_confirma_chat_proprio(
    client, atendente_token, fake_repos
):
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE", atendente_id=atendente["id"])
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVIDO"


@pytest.mark.asyncio
async def test_reabrir_chat_resolvido_volta_para_ia(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    resp = await client.patch(
        f"/chats/{chat['id']}/reabrir",
        json={"motivo": "cliente disse que não resolveu"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IA_ANALISANDO"


@pytest.mark.asyncio
async def test_reabrir_chat_novo_retorna_409(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "NOVO")
    resp = await client.patch(
        f"/chats/{chat['id']}/reabrir", headers=_auth(admin_token)
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_mensagem_do_cliente_reabre_chat_resolvido(client, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "chat_id": chat["id"],
            "whatsapp_number": "5511999990000",
            "remetente": "cliente",
            "conteudo": "Na verdade não resolveu",
        },
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )
    assert resp.status_code == 201
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "IA_ANALISANDO"


@pytest.mark.asyncio
async def test_mensagem_do_atendente_nao_reabre(client, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    await client.post(
        "/webhooks/mensagem",
        json={
            "chat_id": chat["id"],
            "whatsapp_number": "5511999990000",
            "remetente": "atendente",
            "conteudo": "fechando o chamado",
        },
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "RESOLVIDO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ciclo_resolucao.py -v`
Expected: FAIL com 404 nas rotas `confirmar-resolucao`/`reabrir` e status `RESOLVIDO` mantido após a mensagem do cliente

- [ ] **Step 3: Write minimal implementation**

Em `backend/app/services/chat_service.py`:

```python
    async def confirmar_resolucao(self, chat_id: str, user: dict) -> dict:
        """Cenário A: o cliente confirma que a solução da IA funcionou."""
        chat = await self.obter(chat_id)
        if chat["status"] != StatusChat.aguardando_cliente.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Só é possível confirmar chats aguardando o cliente",
            )
        if user["perfil"] == "atendente" and chat.get("atendente_id") not in (
            None,
            user["id"],
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat pertence a outro atendente",
            )
        return await self.atualizar_status(chat_id, StatusChat.resolvido)

    async def reabrir(
        self, chat_id: str, user: dict, motivo: str | None = None
    ) -> dict:
        """Cliente informou que não resolveu: volta para a análise da IA."""
        chat = await self.obter(chat_id)
        if chat["status"] not in (
            StatusChat.resolvido.value,
            StatusChat.aguardando_cliente.value,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Só é possível reabrir chats resolvidos ou aguardando o cliente",
            )
        if user["perfil"] == "atendente" and chat.get("atendente_id") not in (
            None,
            user["id"],
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat pertence a outro atendente",
            )
        return await self.atualizar_status(chat_id, StatusChat.ia_analisando)
```

Em `backend/app/services/webhook_service.py`, dentro de `receber_mensagem`, logo após `repos.chats.update(chat_id, {"ultima_mensagem_em": ...})`:

```python
        if remetente.value == "cliente":
            chat = await self.repos.chats.get(chat_id)
            if chat and chat["status"] == StatusChat.resolvido.value:
                await ChatService(self.repos).atualizar_status(
                    chat_id, StatusChat.ia_analisando
                )
```

(importar `from app.services.chat_service import ChatService` — `chat_service` não importa `webhook_service`, então não há ciclo)

> `atualizar_status` copia o dicionário antes de mutar; não usar `StatusChat.resolvido` (membro) em comparação com string.

Em `backend/app/schemas/chat.py`:

```python
class ChatReabrir(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)
```

Em `backend/app/api/routes/chats.py`:

```python
@router.patch("/{chat_id}/confirmar-resolucao", response_model=ChatDetailResponse)
async def confirmar_resolucao(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.confirmar_resolucao(chat_id, user)


@router.patch("/{chat_id}/reabrir", response_model=ChatDetailResponse)
async def reabrir_chat(
    chat_id: str,
    body: ChatReabrir,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.reabrir(chat_id, user, motivo=body.motivo)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ciclo_resolucao.py -v`
Expected: PASS (8 testes)

- [ ] **Step 5: Run the full suite + ruff**

Run: `cd backend && pytest tests/ -q && ruff check app tests`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/services/webhook_service.py backend/app/api/routes/chats.py backend/app/schemas/chat.py backend/tests/test_ciclo_resolucao.py
git commit -m "feat(chats): confirmacao de resolucao e reabertura do cenario A

- PATCH /chats/{id}/confirmar-resolucao (AGUARDANDO_CLIENTE -> RESOLVIDO)
- PATCH /chats/{id}/reabrir (RESOLVIDO/AGUARDANDO_CLIENTE -> IA_ANALISANDO)
- mensagem do cliente reabre chat RESOLVIDO automaticamente
- atendente so age em chat proprio; admin/supervisor em qualquer um"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 01 e 05)**

```
| 01-4 | Cenário A não alcança `RESOLVIDO` pela IA: `resolvido_pela_ia` leva a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **CORRIGIDO (backend)** — `ChatService.confirmar_resolucao` fecha o ciclo A; botão na Task F4.11 |
| 01-11 | Sem distinção de reabertura/confirmação de resolução pelo cliente além de `RESOLVIDO → IA_ANALISANDO` | `services/chat_service.py:28` | Média | **CORRIGIDO** — `confirmar_resolucao`/`reabrir` explícitos e reabertura automática na mensagem do cliente |
```

```
| 05-4 | Cenário A não tem caminho de fechamento: vai a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **CORRIGIDO (backend)** — `PATCH /chats/{id}/confirmar-resolucao` + reabertura; UI na Task F4.11 |
```

---

## Gate G3 — critério de saída da Fase 3

- [ ] `pytest tests/ -q` verde, com os 4 arquivos de teste novos da fase.
- [ ] `ruff check app tests` sem erro.
- [ ] Intenção não técnica **não** consome Qdrant (testado com contador de embeddings).
- [ ] Baixa confiança gera `ESCLARECIMENTO` + `AGUARDANDO_CLIENTE`, sem transferência.
- [ ] `ia_diagnosticos` grava `intencao`, `categoria_erp`, `departamento_id`, `motivo` e `artigos_consultados` (JSON válido).
- [ ] `chats.departamento_id` só é preenchido em cenários B/C.
- [ ] Ciclo A fecha: `confirmar-resolucao` leva a `RESOLVIDO`; `reabrir` volta a `IA_ANALISANDO`.
- [ ] Registros de Gaps atualizados: 00-8, 01-4, 01-11, 02-19, 05-4, 05-21, 05-23, 08-6 (parcial), 10-7.
- [ ] Passo manual registrado no commit: adicionar `ESCLARECIMENTO` ao enum `status_ia` no Appwrite (gap 02-10).

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

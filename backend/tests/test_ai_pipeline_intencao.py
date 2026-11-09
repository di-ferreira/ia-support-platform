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
    "solucao": "Acesse o módulo fiscal e reenvie a NF-e",
    "instrucoes_cliente": None,
    "precisa_humano": True,
    "referencia": None,
    "confianca": 0.6,
}


def _stub(monkeypatch, classificacao: dict, embedder: ContadorEmbedder, hits: list[dict]):
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm", lambda: FakeLLM(classificacao)
    )
    monkeypatch.setattr(
        "app.services.ai_pipeline.get_llm", lambda: FakeLLM(SOLUCAO_PRONTA)
    )
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: embedder)

    async def _search(embedding, limit: int = 5, categoria: str | None = None):
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

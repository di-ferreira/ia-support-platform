"""Filtro por categoria ERP e limiar minimo de relevancia no RAG."""

import asyncio
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

    asyncio.run(qdrant_service.search_similar([0.1] * 768, limit=5))

    assert fake.kwargs.get("query_filter") is None


def test_limiar_de_relevancia_tem_default_da_spec():
    assert Settings().rag_min_score == 0.35


def test_limiar_fora_de_0_1_e_invalido():
    with pytest.raises(ValidationError):
        Settings(rag_min_score=1.5)


@pytest.mark.asyncio
async def test_hit_abaixo_do_limiar_vira_sem_solucao(client, fake_repos, monkeypatch):
    """Nenhum hit confiavel: cenario C sem chamar o LLM de solucao."""
    from app.services.ai_pipeline import NO_HIT_MENSAGEM
    from app.services.departamento_seed import semear

    await semear(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create({"cliente_id": cliente["id"], "status": "NOVO"})
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

    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: Embedder())

    async def _search(embedding, limit: int = 5, categoria: str | None = None):
        return [
            {
                "id": "a1",
                "score": 0.10,
                "titulo": "irrelevante",
                "conteudo": "nada a ver",
                "categoria": "fiscal",
            }
        ]

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

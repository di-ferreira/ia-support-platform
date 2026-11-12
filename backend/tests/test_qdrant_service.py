"""14-3 — testes diretos de app/services/qdrant_service.py (sem rede; cliente fake).

A dimensão 768 e o ADR-0005 (embedder sempre Ollama) já estão travados em
`test_qdrant_dimensao.py` — aqui não se duplicam.
"""

import uuid

from qdrant_client.http import models

from app.services import qdrant_service
from app.services.qdrant_service import (
    COLLECTION_NAME,
    VECTOR_SIZE,
    article_point_id,
    ensure_collection,
    search_similar,
    upsert_article,
)


class _Hit:
    def __init__(self, point_id, payload, score) -> None:
        self.id = point_id
        self.payload = payload
        self.score = score


class FakeQdrantClient:
    """Substituto do QdrantClient: registra chamadas e responde com hits fixos."""

    def __init__(self, hits: list[_Hit] | None = None, existentes: list[str] | None = None) -> None:
        self.hits = hits or []
        self.existentes = existentes or []
        self.query_calls: list[dict] = []
        self.upserts: list[dict] = []
        self.criadas: list[dict] = []

    def get_collections(self):
        class _Collections:
            collections = [type("_C", (), {"name": n})() for n in self.existentes]

        return _Collections()

    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.criadas.append(
            {"collection_name": collection_name, "vectors_config": vectors_config}
        )

    def query_points(
        self, *, collection_name, query, limit, query_filter, with_payload
    ) -> object:
        self.query_calls.append(
            {
                "collection_name": collection_name,
                "query": query,
                "limit": limit,
                "query_filter": query_filter,
                "with_payload": with_payload,
            }
        )

        class _Response:
            points = self.hits

        return _Response()

    def upsert(self, *, collection_name, wait, points) -> None:
        self.upserts.append(
            {"collection_name": collection_name, "wait": wait, "points": points}
        )


# ---------------------------------------------------------- article_point_id


def test_article_point_id_com_uuid_existente_retorna_o_mesmo_uuid():
    artigo = "5f8a3c2e-9b41-4d2a-8c1e-0a1b2c3d4e5f"
    assert article_point_id(artigo) == artigo
    assert uuid.UUID(article_point_id(artigo)) == uuid.UUID(artigo)


def test_article_point_id_sem_uuid_e_deterministico():
    id_1 = article_point_id("artigo-legado-1")
    id_2 = article_point_id("artigo-legado-1")

    assert id_1 == id_2  # estável para o mesmo id de artigo
    assert article_point_id("artigo-legado-2") != id_1
    uuid.UUID(id_1)  # resultado sempre é UUID válido para o Qdrant


# ------------------------------------------------------------- ensure_collection


async def test_ensure_collection_cria_coleta_com_dimensao_768(monkeypatch):
    fake = FakeQdrantClient()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await ensure_collection()

    assert len(fake.criadas) == 1
    registro = fake.criadas[0]
    assert registro["collection_name"] == COLLECTION_NAME
    assert registro["vectors_config"].size == VECTOR_SIZE == 768
    assert registro["vectors_config"].distance == models.Distance.COSINE


async def test_ensure_collection_eh_noop_quando_coleta_ja_existe(monkeypatch):
    fake = FakeQdrantClient(existentes=[COLLECTION_NAME])
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await ensure_collection()

    assert fake.criadas == []


# ------------------------------------------------------------ search_similar


def _hit(**payload) -> _Hit:
    return _Hit("point-1", payload, 0.91)


async def test_search_similar_sem_categoria_retorna_hits_mapeados(monkeypatch):
    fake = FakeQdrantClient(
        hits=[_hit(article_id="artigo-1", titulo="NF-e", conteudo="texto", categoria="fiscal")]
    )
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    hits = await search_similar([0.1] * 768, limit=3)

    assert hits == [
        {
            "id": "artigo-1",
            "score": 0.91,
            "titulo": "NF-e",
            "conteudo": "texto",
            "categoria": "fiscal",
        }
    ]
    chamada = fake.query_calls[0]
    assert chamada["collection_name"] == COLLECTION_NAME
    assert chamada["query"] == [0.1] * 768
    assert chamada["limit"] == 3
    assert chamada["query_filter"] is None
    assert chamada["with_payload"] is True


async def test_search_similar_com_categoria_aplica_filtro(monkeypatch):
    fake = FakeQdrantClient(hits=[])
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await search_similar([0.1] * 768, categoria="fiscal")

    filtro = fake.query_calls[0]["query_filter"]
    assert isinstance(filtro, models.Filter)
    condicao = filtro.must[0]
    assert condicao.key == "categoria"
    assert isinstance(condicao.match, models.MatchValue)
    assert condicao.match.value == "fiscal"


async def test_search_similar_sem_hits_retorna_lista_vazia(monkeypatch):
    fake = FakeQdrantClient(hits=[])
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    assert await search_similar([0.1] * 768) == []


# ------------------------------------------------------------------- upsert


async def test_upsert_article_gera_pointstruct_com_payload(monkeypatch):
    fake = FakeQdrantClient()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)
    embedding = [0.2] * 768

    await upsert_article("artigo-1", "Título", "Conteúdo", "fiscal", embedding)

    assert len(fake.upserts) == 1
    upsert = fake.upserts[0]
    assert upsert["collection_name"] == COLLECTION_NAME
    assert upsert["wait"] is True
    ponto = upsert["points"][0]
    assert isinstance(ponto, models.PointStruct)
    assert ponto.id == article_point_id("artigo-1")
    assert ponto.vector == embedding
    assert ponto.payload == {
        "article_id": "artigo-1",
        "titulo": "Título",
        "conteudo": "Conteúdo",
        "categoria": "fiscal",
    }


async def test_upsert_article_conteudo_nulo_vira_string_vazia(monkeypatch):
    fake = FakeQdrantClient()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await upsert_article("artigo-2", "Título", None, "estoque", [0.3] * 768)

    assert fake.upserts[0]["points"][0].payload["conteudo"] == ""
